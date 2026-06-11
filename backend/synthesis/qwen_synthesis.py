import csv
import json
from pathlib import Path
from urllib import request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"

SYSTEM_PROMPT = """
You are NatureDesk, a biodiversity assistant.

You may ONLY use the evidence provided.

You must NEVER use external knowledge.

Every factual claim should contain a source citation.

Preferred citation format:

(Source: BON NDVI Time Series, chunk bon-ndvi-timeseries)

Output ONLY one of:

## Answer
...
## Evidence used
...
## Uncertainty and gaps
...
## Assumptions
...
## Human review needed
...

OR

## Refusal
...
""".strip()


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


def validate_answer(answer):

    required = [
        "## Answer",
        "## Evidence used",
        "## Uncertainty and gaps",
        "## Assumptions",
        "## Human review needed",
    ]

    for item in required:
        if item not in answer:
            return False

    # minder streng dan eerst
    if "(Source:" not in answer:
        return False

    return True


def build_refusal(question, reason):

    return f"""## Refusal

I cannot answer "{question}" from the approved evidence.

Reason:
{reason}

What a human should consult instead:
The BON output files and ecological source data.
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


def synthesize(question, csv_path):

    rows = load_csv(csv_path)

    if not rows:
        return build_refusal(
            question,
            "No evidence was found."
        )

    chunk = build_chunk(rows)

    for attempt in range(3):

        answer = call_qwen(question, chunk)

        print("\n===== RAW QWEN OUTPUT =====")
        print(answer)
        print("===========================\n")

        if validate_answer(answer):
            print(f"Qwen synthesis succeeded on attempt {attempt + 1}")
            return answer

        print(f"Validation failed on attempt {attempt + 1}")

    return build_refusal(
        question,
        "The language model repeatedly failed validation."
    )


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
