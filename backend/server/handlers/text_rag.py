"""Safe text evidence handler that refuses when quote/synthesis gates are closed."""

from __future__ import annotations

import json
from pathlib import Path

from frozen_evidence import EvidenceGateResult
from handlers import approved_rows_for_route, concise_gate_refusal, safe_refusal


TEXT_FIELDS = ("text", "chunk_text", "content", "body", "preview")


def handle_text_rag(question: str, gate: EvidenceGateResult):
    rows = approved_rows_for_route("text_rag", gate)
    if not rows:
        return concise_gate_refusal("text-evidence")

    row = rows[0]
    readiness = row.readiness
    if readiness.get("quote_allowed") is not True or readiness.get("citation_ready") is not True:
        return safe_refusal(
            "readiness_gate_blocked",
            (
                "Approved text evidence is listed, but quote/citation readiness gates "
                "are closed, so I cannot provide a factual text answer from this route."
            ),
        )

    chunk = _first_jsonl_chunk(row.path)
    if chunk is None:
        return safe_refusal(
            "no_approved_evidence",
            "I cannot answer from text evidence because the approved JSONL artifact is unreadable.",
        )

    return safe_refusal(
        "backend_pipeline_not_connected",
        (
            "Approved text evidence is readable, but the demo text retriever does not "
            "yet rank chunks or synthesize answers."
        ),
    )


def _first_jsonl_chunk(path: str) -> dict | None:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict) and any(payload.get(field) for field in TEXT_FIELDS):
                    return payload
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return None
