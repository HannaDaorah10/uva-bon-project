import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

DATE_CANDIDATES = ["date", "time", "datetime", "system:time_start"]
NDVI_CANDIDATES = ["NDVI", "ndvi", "mean", "median", "value"]


def find_key(row, candidates):
    lower = {k.lower(): k for k in row.keys()}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    raise ValueError(f"Could not find any of these columns: {candidates}")


def read_rows(path: Path):
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            data = data.get("data", data.get("rows", []))
        return data
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(value, key):
    if key == "system:time_start":
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = read_rows(Path(args.input))
    if not rows:
        raise ValueError("No rows found")

    date_key = find_key(rows[0], DATE_CANDIDATES)
    ndvi_key = find_key(rows[0], NDVI_CANDIDATES)

    clean = []
    for row in rows:
        clean.append({
            "date": parse_date(row[date_key], date_key),
            "feature_index": row.get("feature_index", 0),
            "NDVI": float(row[ndvi_key]),
        })

    clean.sort(key=lambda row: row["date"])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "feature_index", "NDVI"])
        writer.writeheader()
        writer.writerows(clean)

    print(f"Wrote {out}")
    print(clean[:5])


if __name__ == "__main__":
    main()