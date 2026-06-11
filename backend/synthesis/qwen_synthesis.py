import csv
import json
import sys
from pathlib import Path
from urllib import request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"

PROMPT_PATH = Path(__file__).parent / "synthesis_prompt.md"


def load_system_prompt():
    base_prompt = PROMPT_PATH.read_text()

    ndvi_rules = """
---

## Additional NDVI synthesis rules

For NDVI evidence, do NOT infer:

- vegetation health
- biodiversity condition
- ecological quality
- environmental causes
- land-cover change
- plant stress
- recovery
- improvement

Only describe numerical NDVI values present in the evidence.

Allowed statements:

- observed NDVI values
- minimum NDVI value
- maximum NDVI value
- first NDVI value
- final NDVI value
- increases
- decreases
- fluctuations

Do not interpret what NDVI values mean ecologically unless that explanation is explicitly present in the evidence.

For this task, use this citation whenever making a factual claim from the NDVI evidence:

(Source: BON NDVI Time Series, chunk bon-ndvi-timeseries)

Do not output markdown code fences.
Do not output explanations outside the required NatureDesk template.
"""

    return base_prompt + "\n\n" + ndvi_rules


SYSTEM_PROMPT = load_system_prompt()


def load_csv(csv_path):

    rows = []

    with open(csv_path, newline="") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            rows.append(row)

    return rows


def build_chunk(rows):

    evidence_lines = []

    for row in rows[:50]:
        evidence_lines.append(
            f"date={row['date']}, "
            f"feature_index={row['feature_index']}, "
            f"NDVI={row['NDVI']}"
        )

    evidence_text = "\n".join(evidence_lines)

    return f"""
--- CHUNK ---
chunk_id: bon-ndvi-timeseries
title: BON NDVI Time Series
citation_string: Local BON NDVI pipeline output
source_family: BON pipeline output
readiness_label: challenge-approved

text:
{evidence_text}

--- END CHUNK ---
"""


def call_qwen(question, chunk):

    prompt = f"""
Question:
{question}

Approved evidence:

{chunk}
"""

    payload = {
        "model": MODEL,
        "prompt": SYSTEM_PROMPT + "\n\n" + prompt,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    req = request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=300) as response:
        result = json.loads(response.read().decode())

    return result["response"]


def build_refusal(question):

    return f"""## Refusal

I cannot answer "{question}" from the approved evidence.

Reason:
No usable evidence was available.

What a human should consult instead:
The BON output files and ecological source data.
"""


def synthesize(question, csv_path):

    rows = load_csv(csv_path)

    if not rows:
        return build_refusal(question)

    chunk = build_chunk(rows)

    answer = call_qwen(
        question=question,
        chunk=chunk
    )

    print("\n===== RAW QWEN OUTPUT =====\n", file=sys.stderr)
    print(answer, file=sys.stderr)
    print("\n===========================\n", file=sys.stderr)

    return answer


if __name__ == "__main__":

    question = (
        "How did NDVI change during the 2024 growing season "
        "in Zuid-Holland?"
    )

    csv_path = (
        "../inputRouting/runs/20260610-175715/timeseries.csv"
    )

    answer = synthesize(
        question=question,
        csv_path=csv_path
    )

    print(answer)
