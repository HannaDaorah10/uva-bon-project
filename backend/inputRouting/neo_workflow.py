import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error, parse

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
BON_BASE_URL = "http://127.0.0.1:3001"
PIPELINE_PATH = "Netherlands_neo_signaleyes_boombasis_pipeline_41.json"
SCRIPT_NODE = "data>queryNeoSignalEyes.yml@0"
OUTPUT_ROOT = "/sources/commercial_internal/neo_signaleyes/den_haag_2026-06-15"

SYSTEM_PROMPT = """
You translate user requests into a small BON-in-a-Box NEO SignalEyes / Boombasis intent JSON.
Return ONLY valid JSON. No markdown. No explanation.

Required JSON schema:
{
 "pipeline": "neo",
 "mode": "metadata" or "tiny_aoi" or "full_city",
 "entities": ["crown"] or ["centerpoint"] or ["crown", "centerpoint"],
 "max_pages": number or null,
 "admin_unit_level": "gm0518" or "stadsdeel" or "wijk" or "buurt" or "tile",
 "admin_unit_preset": string,
 "metric_theme": "all_metric_themes" or "source_capture_provenance" or "crown_count" or "centerpoint_count" or "crown_area" or "crown_diameter" or "height" or "method_date_quality" or "naturedesk_proxy_crosswalk"
}

Defaults:
- For first tests/smoke tests: mode=tiny_aoi, entities=["crown", "centerpoint"], max_pages=1.
- For metadata questions: mode=metadata, entities=["crown", "centerpoint"], max_pages=null.
- For full Den Haag / GM0518 runs: mode=full_city, entities=["crown", "centerpoint"], max_pages=null, admin_unit_level=gm0518, admin_unit_preset=GM0518.
- Default admin_unit_level=wijk, admin_unit_preset=all_wijken, metric_theme=all_metric_themes.
- Do not create BON internal keys.
- Do not output credentials, base URLs, output_root, WKT polygons, or API passwords.
- NEO is a licensed comparator/reference layer, not ground truth or validation.
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
            raise ValueError(f"No JSON found in model output: {text}")
        return json.loads(match.group(0))


def prompt_to_intent(prompt: str) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": SYSTEM_PROMPT + "User request: " + prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    result = http_json(OLLAMA_URL, payload)
    return extract_json(result["response"])


def apply_defaults(cfg: dict) -> dict:
    cfg = dict(cfg)

    cfg.setdefault("pipeline", "neo")
    cfg.setdefault("mode", "tiny_aoi")
    cfg.setdefault("entities", ["crown", "centerpoint"])
    cfg.setdefault("admin_unit_level", "wijk")
    cfg.setdefault("admin_unit_preset", "all_wijken")
    cfg.setdefault("metric_theme", "all_metric_themes")

    if cfg.get("max_pages") is None:
        if cfg["mode"] == "tiny_aoi":
            cfg["max_pages"] = 1
        else:
            cfg["max_pages"] = None

    if cfg["mode"] == "full_city":
        cfg["admin_unit_level"] = cfg.get("admin_unit_level") or "gm0518"
        cfg["admin_unit_preset"] = cfg.get("admin_unit_preset") or "GM0518"
        cfg["max_pages"] = cfg.get("max_pages", None)

    return cfg


def validate_intent(cfg: dict):
    required = [
        "pipeline",
        "mode",
        "entities",
        "max_pages",
        "admin_unit_level",
        "admin_unit_preset",
        "metric_theme",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")

    if cfg["pipeline"] != "neo":
        raise ValueError("Only pipeline=neo is supported")

    if cfg["mode"] not in {"metadata", "tiny_aoi", "full_city"}:
        raise ValueError("mode must be metadata, tiny_aoi, or full_city")

    if not isinstance(cfg["entities"], list) or not cfg["entities"]:
        raise ValueError("entities must be a non-empty list")

    allowed_entities = {"crown", "centerpoint"}
    invalid_entities = sorted(set(cfg["entities"]) - allowed_entities)
    if invalid_entities:
        raise ValueError(f"Unsupported entities: {invalid_entities}")

    if cfg["max_pages"] is not None:
        if not isinstance(cfg["max_pages"], int) or cfg["max_pages"] < 1:
            raise ValueError("max_pages must be a positive integer or null")

    if cfg["admin_unit_level"] not in {"gm0518", "stadsdeel", "wijk", "buurt", "tile"}:
        raise ValueError("admin_unit_level is not supported")

    allowed_metric_themes = {
        "all_metric_themes",
        "source_capture_provenance",
        "crown_count",
        "centerpoint_count",
        "crown_area",
        "crown_diameter",
        "height",
        "method_date_quality",
        "naturedesk_proxy_crosswalk",
    }
    if cfg["metric_theme"] not in allowed_metric_themes:
        raise ValueError("metric_theme is not supported")


def build_bon_payload(cfg: dict) -> dict:
    return {
        f"{SCRIPT_NODE}|mode": cfg["mode"],
        f"{SCRIPT_NODE}|entities": cfg["entities"],
        f"{SCRIPT_NODE}|output_root": OUTPUT_ROOT,
        f"{SCRIPT_NODE}|max_pages": cfg["max_pages"],
        f"{SCRIPT_NODE}|admin_unit_level": cfg["admin_unit_level"],
        f"{SCRIPT_NODE}|admin_unit_preset": cfg["admin_unit_preset"],
        f"{SCRIPT_NODE}|metric_theme": cfg["metric_theme"],
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


def find_neo_output_folder(output_folders: dict) -> str:
    direct = output_folders.get(SCRIPT_NODE)
    if direct:
        return direct
    for key, value in output_folders.items():
        if "queryNeoSignalEyes" in key:
            return value
    raise RuntimeError("Could not find NEO queryNeoSignalEyes output folder")

def download(url: str, out: Path, required=True, attempts=20, delay_seconds=2):
    out.parent.mkdir(parents=True, exist_ok=True)

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with request.urlopen(url, timeout=120) as response:
                out.write_bytes(response.read())
            print(f"Downloaded {out}")
            return
        except error.HTTPError as exc:
            last_error = exc
            if exc.code == 404 and attempt < attempts:
                print(f"Output not ready yet, retry {attempt}/{attempts}: {url}")
                time.sleep(delay_seconds)
                continue

            if required:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Download failed: {url} -> HTTP {exc.code} {body}") from exc

            print(f"Skipped missing optional output: {url}")
            return

    if required and last_error is not None:
        raise RuntimeError(f"Download failed after retries: {url}") from last_error



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--runs-dir", default="runs")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.runs_dir) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "prompt.txt").write_text(args.prompt)

    print("1. Prompt -> NEO intent JSON")
    cfg = apply_defaults(prompt_to_intent(args.prompt))
    validate_intent(cfg)
    (run_dir / "llm_config.json").write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg, indent=2))
    print("2. Intent JSON -> BON input JSON")

    bon_payload = build_bon_payload(cfg)
    (run_dir / "bon_run_input.json").write_text(json.dumps(bon_payload, indent=2))

    print("3. Start BON run")
    run_id = post_to_bon(bon_payload).strip()
    (run_dir / "bon_run_response.txt").write_text(run_id)
    print(f"Run id: {run_id}")

    print("4. Get output folders")
    output_folders = get_output_folders(run_id)
    (run_dir / "output_folders.json").write_text(json.dumps(output_folders, indent=2))
    print(json.dumps(output_folders, indent=2))

    neo_folder = find_neo_output_folder(output_folders)

    print("5. Download known NEO outputs")
    base = f"{BON_BASE_URL.rstrip('/')}/output/{neo_folder}"
    mode = cfg["mode"]

    download(f"{base}/neo_signaleyes_pipeline41_summary.json", run_dir / "neo_signaleyes_pipeline41_summary.json")
    download(f"{base}/neo_signaleyes_pipeline41_{mode}_provenance.json", run_dir / f"neo_signaleyes_pipeline41_{mode}_provenance.json")
    download(f"{base}/neo_signaleyes_pipeline41_{mode}_counts.json", run_dir / f"neo_signaleyes_pipeline41_{mode}_counts.json")
    download(f"{base}/neo_signaleyes_pipeline41_{mode}_checksums.sha256", run_dir / f"neo_signaleyes_pipeline41_{mode}_checksums.sha256")

    download(f"{base}/neo_signaleyes_pipeline41_crown_map_preview.geojson", run_dir / "neo_signaleyes_pipeline41_crown_map_preview.geojson", required=False)
    download(f"{base}/neo_signaleyes_pipeline41_centerpoint_map_preview.geojson", run_dir / "neo_signaleyes_pipeline41_centerpoint_map_preview.geojson", required=False)

    print("Done")
    print(f"Run folder: {run_dir}")


if __name__ == "__main__":
    main()