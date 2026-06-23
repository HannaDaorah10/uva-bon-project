import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib import request, error, parse

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
BON_BASE_URL = "http://127.0.0.1:3001"
PIPELINE_PATH = "ndvi_pipeline.json"

SYSTEM_PROMPT = """
You translate user requests into a small BON-in-a-Box NDVI intent JSON.
Return ONLY valid JSON. No markdown. No explanation.

Required JSON schema:
{
  "pipeline": "ndvi",
  "area": "Zuid-Holland" or "Den Haag",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "spatial_resolution": number,
  "summary_statistic": "mean" or "median" or "min" or "max",
  "crs": "EPSG:4326" or "EPSG:28992"
}

Defaults:
- Zuid-Holland: 2024-05-01 to 2024-09-30, median, EPSG:4326, 0.001
- Den Haag: 2024-05-01 to 2024-09-30, median, EPSG:4326, 0.0002
- Prefer median unless the user explicitly asks for mean, min, or max.
- Do not create BON internal keys.
- Do not output bbox_crs or study_area_polygon; those come from the BON template.
""".strip()


def http_json(url, payload, timeout=120):
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in model output:{text}")
        return json.loads(match.group(0))


def prompt_to_intent(prompt: str) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": SYSTEM_PROMPT + "User request:" + prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    result = http_json(OLLAMA_URL, payload)
    return extract_json(result["response"])


def parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD, got {value}") from exc


def validate_intent(cfg: dict):
    required = ["pipeline", "area", "start_date", "end_date", "spatial_resolution", "summary_statistic", "crs"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")
    if cfg["pipeline"] != "ndvi":
        raise ValueError("Only pipeline=ndvi is supported")
    if cfg["summary_statistic"] not in {"mean", "median", "min", "max"}:
        raise ValueError("summary_statistic must be mean, median, min, or max")
    start = parse_date(cfg["start_date"], "start_date")
    end = parse_date(cfg["end_date"], "end_date")
    if end < start:
        raise ValueError("end_date must be after start_date")
    
def build_bon_payload(template: dict, cfg: dict) -> dict:
    if "bbox_crs" not in template:
        raise KeyError("Template must contain bbox_crs")
    return {
        "pipeline@210": template["bbox_crs"],
        "data>load_polygons.yml@211|polygon_type": "Country or region",
        "NDVI>calculateNDVI.yml@199|start_date": cfg["start_date"],
        "NDVI>calculateNDVI.yml@199|end_date": cfg["end_date"],
        "NDVI>calculateNDVI.yml@199|spatial_resolution": float(cfg["spatial_resolution"]),
        "NDVI>calculateNDVI.yml@199|summary_statistic": cfg["summary_statistic"],
    }


def post_to_bon(payload: dict) -> str:
    url = f"{BON_BASE_URL.rstrip('/')}/pipeline/{PIPELINE_PATH}/run"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"accept": "text/plain", "Content-Type": "text/plain"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            return response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BON HTTP {exc.code} {exc.reason} {body}") from exc


def get_output_folders(run_id: str) -> dict:
    encoded = parse.quote(run_id, safe="")
    url = f"{BON_BASE_URL.rstrip('/')}/pipeline/{encoded}/outputs"
    with request.urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    with request.urlopen(url, timeout=120) as response:
        out.write_bytes(response.read())
    print(f"Downloaded {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--template", default="templates/bon_ndvi_template.json")
    parser.add_argument("--runs-dir", default="runs")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.runs_dir) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "prompt.txt").write_text(args.prompt)

    print("1. Prompt -> intent JSON")
    cfg = prompt_to_intent(args.prompt)
    validate_intent(cfg)
    (run_dir / "llm_config.json").write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg, indent=2))

    print("2. Intent JSON -> BON input JSON")
    template = json.loads(Path(args.template).read_text())
    bon_payload = build_bon_payload(template, cfg)
    (run_dir / "bon_run_input.json").write_text(json.dumps(bon_payload, indent=2))

    print("3. Start BON run")
    run_id = post_to_bon(bon_payload).strip()
    (run_dir / "bon_run_response.txt").write_text(run_id)
    print(f"Run id: {run_id}")

    print("4. Get output folders")
    output_folders = get_output_folders(run_id)
    (run_dir / "output_folders.json").write_text(json.dumps(output_folders, indent=2))
    print(json.dumps(output_folders, indent=2))

    ndvi_folder = output_folders.get("NDVI>calculateNDVI.yml@199")
    if not ndvi_folder:
        raise RuntimeError("Could not find NDVI output folder")

    print("5. Download known outputs")
    base = f"{BON_BASE_URL.rstrip('/')}/output/{ndvi_folder}"
    download(f"{base}/timeseries.csv", run_dir / "timeseries.csv")
    download(f"{base}/ndvi_timeseries.png", run_dir / "ndvi_timeseries.png")

    print("Done")
    print(f"Run folder: {run_dir}")


if __name__ == "__main__":
    main()
