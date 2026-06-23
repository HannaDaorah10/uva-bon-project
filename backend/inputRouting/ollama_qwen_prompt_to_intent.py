import argparse
import json
import re
from pathlib import Path
from urllib import request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"

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


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in model output: {text}")
        return json.loads(match.group(0))


def prompt_to_intent(user_prompt: str) -> dict:
    payload = {
        "model": MODEL,
        "prompt": SYSTEM_PROMPT + "User request:" + user_prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0}
    }

    req = request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    return extract_json(result["response"])


def validate(cfg: dict) -> None:
    required = ["pipeline", "area", "start_date", "end_date", "spatial_resolution", "summary_statistic", "crs"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing keys: {missing}")
    if cfg["pipeline"] != "ndvi":
        raise ValueError("Only ndvi is supported")
    if cfg["area"] not in {"Zuid-Holland", "Den Haag"}:
        raise ValueError("Unsupported area")
    if cfg["summary_statistic"] not in {"mean", "median", "min", "max"}:
        raise ValueError("Invalid summary_statistic")
    if cfg["crs"] == "EPSG:4326" and float(cfg["spatial_resolution"]) >= 1:
        raise ValueError("EPSG:4326 uses degrees, for example 0.001")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="Natural language BON request")
    parser.add_argument("--out", default="runs/demo/llm_config.json")
    args = parser.parse_args()

    cfg = prompt_to_intent(args.prompt)
    validate(cfg)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()