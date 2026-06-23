import argparse
import json
from datetime import date
from pathlib import Path
from urllib import request, error


def parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} moet YYYY-MM-DD zijn, niet {value}") from exc


def validate_intent(cfg: dict):
    required = ["pipeline", "area", "start_date", "end_date", "spatial_resolution", "summary_statistic", "crs"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")
    if cfg["pipeline"] != "ndvi":
        raise ValueError("Only pipeline=ndvi is supported")

    start = parse_date(cfg["start_date"], "start_date")
    end = parse_date(cfg["end_date"], "end_date")
    if end < start:
        raise ValueError("end_date moet na start_date liggen")
    if start.year < 2017:
        raise ValueError("Sentinel-2 start_date moet 2017 of later zijn")
    if cfg["summary_statistic"] not in {"mean", "median", "min", "max"}:
        raise ValueError("summary_statistic moet mean, median, min of max zijn")


def build_bon_payload(template: dict, cfg: dict) -> dict:
    if "bbox_crs" not in template:
        raise KeyError("Template mist bbox_crs. Gebruik de BON input JSON waarin bbox_crs staat.")

    return {
        "pipeline@210": template["bbox_crs"],
        "data>load_polygons.yml@211|polygon_type": "Country or region",
        "NDVI>calculateNDVI.yml@199|start_date": cfg["start_date"],
        "NDVI>calculateNDVI.yml@199|end_date": cfg["end_date"],
        "NDVI>calculateNDVI.yml@199|spatial_resolution": float(cfg["spatial_resolution"]),
        "NDVI>calculateNDVI.yml@199|summary_statistic": cfg["summary_statistic"],
    }


def post_to_bon(payload: dict, bon_base_url: str, pipeline_path: str) -> str:
    url = f"{bon_base_url.rstrip('/')}/pipeline/{pipeline_path}/run"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"accept": "text/plain", "Content-Type": "text/plain"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            return response.read().decode("utf-8")
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"BON HTTP {exc.code} {exc.reason} URL: {url} Response body: {response_body}"
        ) from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="runs/demo/llm_config.json")
    parser.add_argument("--template", default="templates/bon_ndvi_template.json")
    parser.add_argument("--out", default="runs/demo/bon_run_input.json")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--bon-base-url", default="http://127.0.0.1:3001")
    parser.add_argument("--pipeline-path", default="ndvi_pipeline.json")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    validate_intent(cfg)

    template = json.loads(Path(args.template).read_text())
    payload = build_bon_payload(template, cfg)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out}")

    print("BON API payload keys:")
    for key, value in payload.items():
        if key == "pipeline@210":
            print(f"  {key}: bbox_crs object")
        else:
            print(f"  {key}: {value}")

    if not args.run:
        print("Dry run only. Add --run to post to BON.")
        return

    result = post_to_bon(payload, args.bon_base_url, args.pipeline_path)
    response_path = out.parent / "bon_run_response.txt"
    response_path.write_text(result)
    print(result)
    print(f"Wrote {response_path}")


if __name__ == "__main__":
    main()