"""Lexical text retrieval handler for approved frozen JSONL evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from frozen_evidence import EvidenceGateResult
from handlers import HandlerResponse, approved_rows_for_route, citation_for_row, concise_gate_refusal, safe_refusal
from synthesis import synthesize_text_answer


TEXT_FIELDS = ("text", "chunk_text", "content", "body", "preview")
TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
MAX_CHUNKS = 3


def handle_text_rag(question: str, gate: EvidenceGateResult) -> HandlerResponse:
    rows = approved_rows_for_route("text_rag", gate)
    if not rows:
        return concise_gate_refusal("text-evidence")

    row = rows[0]
    chunks = retrieve_text_chunks(question, row.path)
    if not chunks:
        return safe_refusal(
            "no_approved_evidence",
            "I cannot answer from text evidence because no matching approved chunks were retrieved.",
        )

    return HandlerResponse(
        refused=False,
        answer=synthesize_text_answer(question, chunks),
        citations=[citation_for_row(row)],
    )


def retrieve_text_chunks(question: str, path: str, limit: int = MAX_CHUNKS) -> list[dict[str, Any]]:
    question_tokens = _tokens(question)
    if not question_tokens:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not _chunk_is_allowed(chunk):
                    continue
                text = _chunk_text(chunk)
                if not text:
                    continue
                score = len(question_tokens & _tokens(text + " " + str(chunk.get("title", ""))))
                if score > 0:
                    scored.append((score, chunk))
    except (OSError, UnicodeDecodeError):
        return []

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _score, chunk in scored[:limit]]


def _chunk_is_allowed(chunk: dict[str, Any]) -> bool:
    return (
        chunk.get("retrieve_allowed") is True
        and chunk.get("quote_allowed") is True
        and chunk.get("export_allowed") is False
        and chunk.get("share_external_llm_allowed") is False
        and chunk.get("train_allowed") is False
    )


def _chunk_text(chunk: dict[str, Any]) -> str:
    for field in TEXT_FIELDS:
        value = chunk.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _tokens(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.lower()))
