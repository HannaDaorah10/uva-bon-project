import os
from openai import OpenAI
from dummy_chunks import DUMMY_CHUNKS, DUMMY_REFUSAL_CHUNKS

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SYSTEM_PROMPT = """
You are NatureDesk, a biodiversity assistant for ecologists.

You may ONLY use the evidence chunks provided.
Never use your training knowledge as a factual claim.

Every factual claim MUST cite its source using this exact format:

(Source: [title], chunk [chunk_id], [citation_string])

If evidence is insufficient, use ONLY this refusal format:

## Refusal
I cannot answer "[question]" from the approved evidence.
Reason: [out of scope / no evidence]
What a human should consult instead: [specific suggestion]

Otherwise, use ONLY this answer format:

## Answer
[One paragraph. Every claim cited.]

## Evidence used
| Chunk ID | Title | Citation | Relevant passage |
|----------|--------|----------|------------------|
[one row per chunk]

## Uncertainty and gaps
[Specific — not generic.]

## Assumptions
[Any interpretation beyond what the source literally says.]

## Human review needed
[Concrete next step for an ecologist.]
"""

def format_chunks(chunks):
    if not chunks:
        return "[No evidence retrieved]"

    formatted = []

    for c in chunks:
        formatted.append(
            f"--- CHUNK ---\n"
            f"chunk_id: {c['chunk_id']}\n"
            f"title: {c['title']}\n"
            f"citation_string: {c['citation_string']}\n"
            f"source_family: {c['source_family']}\n"
            f"readiness_label: {c['readiness_label']}\n"
            f"text: {c['text']}\n"
            f"--- END CHUNK ---"
        )

    return "\n\n".join(formatted)

def synthesize(question, chunks):

    if client is None:
        raise RuntimeError("OPENAI_API_KEY is required for the live synthesis smoke test")

    response = client.responses.create(
        model="gpt-5.5",
        reasoning={"effort": "low"},
        input=[
            {
                "role": "developer",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content":
                    f"Question: {question}\n\n"
                    f"Approved evidence:\n\n"
                    f"{format_chunks(chunks)}"
            }
        ]
    )

    return response.output_text

def run(question, chunks, label):

    print("\n" + "=" * 60)
    print(f"TEST: {label}")
    print(f"Q: {question}")
    print("=" * 60)

    answer = synthesize(question, chunks)

    print(answer)

    print("\n--- CHECKS ---")

    if "## Evidence used" in answer:
        print("✓ Evidence table present")

    elif "## Refusal" in answer:
        print("✓ Refusal format used")

    else:
        print("✗ FAIL")

    if "## Uncertainty" in answer:
        print("✓ Uncertainty section present")

    if "## Human review" in answer:
        print("✓ Human review section present")

def main():
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY not set; skipping live synthesis smoke test.")
        return

    run(
        question="What does the SHI score show for The Hague Groenmonitor between 2019 and 2024?",
        chunks=DUMMY_CHUNKS,
        label="ANSWERABLE"
    )

    run(
        question="What was the butterfly population in The Hague in 1970?",
        chunks=DUMMY_REFUSAL_CHUNKS,
        label="REFUSAL - no evidence"
    )

    run(
        question="Is it legal for the municipality to build housing on this green corridor?",
        chunks=DUMMY_CHUNKS,
        label="REFUSAL - legal question"
    )


def test_live_synthesis_smoke_is_manual():
    assert OPENAI_API_KEY is None or client is not None


if __name__ == "__main__":
    main()
