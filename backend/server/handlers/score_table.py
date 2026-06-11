"""Minimal safe handler for approved frozen score tables."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from frozen_evidence import EvidenceGateResult, FrozenEvidenceRow
from handlers import (
    HandlerResponse,
    approved_rows_for_route,
    citation_for_row,
    concise_gate_refusal,
    route_caveat_sentence,
    safe_refusal,
    truncate,
)


TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def handle_score_table(question: str, gate: EvidenceGateResult) -> HandlerResponse:
    rows = approved_rows_for_route("score_table", gate)
    if not rows:
        return concise_gate_refusal("score-table")

    ranked_rows = sorted(
        rows,
        key=lambda row: _question_overlap(question, str(row.raw.get("relative_path", row.path))),
        reverse=True,
    )

    for row in ranked_rows:
        table = _read_table_preview(row)
        if table is None:
            continue
        fields, first_row, row_count = table
        relative_path = str(row.raw.get("relative_path", Path(row.path).name))
        answer = _answer_from_preview(relative_path, fields, first_row, row_count)
        return HandlerResponse(
            refused=False,
            answer=answer,
            citations=[citation_for_row(row)],
        )

    return safe_refusal(
        "no_approved_evidence",
        "I cannot answer from score tables because the approved CSV evidence is unreadable.",
    )


def _read_table_preview(row: FrozenEvidenceRow) -> tuple[list[str], dict[str, str], int] | None:
    try:
        with Path(row.path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = [field for field in (reader.fieldnames or []) if field]
            first_row: dict[str, str] | None = None
            row_count = 0
            for item in reader:
                if first_row is None:
                    first_row = {key: item.get(key, "") for key in fields}
                row_count += 1
    except (OSError, csv.Error, UnicodeDecodeError):
        return None

    if not fields or first_row is None:
        return None
    return fields, first_row, row_count


def _answer_from_preview(
    relative_path: str,
    fields: list[str],
    first_row: dict[str, str],
    row_count: int,
) -> str:
    shown_fields = ", ".join(fields[:8])
    shown_cells = "; ".join(
        f"{field}={truncate(first_row.get(field, ''), 80)}" for field in fields[:6]
    )
    return (
        f"Approved score-table evidence is readable: `{relative_path}`. "
        f"Rows detected: {row_count}. Columns include: {shown_fields}. "
        f"First available row preview: {shown_cells}. "
        f"{route_caveat_sentence()}"
    )


def _question_overlap(question: str, value: str) -> int:
    question_tokens = set(TOKEN_RE.findall(question.lower()))
    value_tokens = set(TOKEN_RE.findall(value.lower()))
    return len(question_tokens & value_tokens)
