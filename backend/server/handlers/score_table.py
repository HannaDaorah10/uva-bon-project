"""Safe retrieval handler for approved frozen score tables."""

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
    safe_refusal,
)
from synthesis import synthesize_crown_surface_answer, synthesize_score_table_preview


TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
CROWN_SURFACE_RE = re.compile(
    r"(crown\s+surface|crown\s+area|tree\s+crown\s+area|kroonoppervlakte|kroon\s+oppervlakte)",
    re.IGNORECASE,
)
THE_HAGUE_RE = re.compile(r"(the\s+hague|den\s+haag|'s-gravenhage|gemeente\s+den\s+haag|gm0518)", re.IGNORECASE)
YEAR_2021_RE = re.compile(r"(2021|end\s+of\s+2021|eind\s+van\s+2021)", re.IGNORECASE)


def handle_score_table(question: str, gate: EvidenceGateResult) -> HandlerResponse:
    rows = approved_rows_for_route("score_table", gate)
    if not rows:
        return concise_gate_refusal("score-table")

    if _is_crown_surface_question(question):
        crown_answer = _answer_crown_surface_question(rows)
        if crown_answer is not None:
            answer, source_row = crown_answer
            return HandlerResponse(
                refused=False,
                answer=answer,
                citations=[citation_for_row(source_row)],
            )

    ranked_rows = sorted(
        rows,
        key=lambda row: _question_overlap(question, str(row.raw.get("relative_path", row.path))),
        reverse=True,
    )

    for row in ranked_rows:
        table = _read_table(row)
        if table is None:
            continue
        fields, records = table
        if not records:
            continue
        relative_path = str(row.raw.get("relative_path", Path(row.path).name))
        answer = synthesize_score_table_preview(relative_path, fields, records[0], len(records))
        return HandlerResponse(
            refused=False,
            answer=answer,
            citations=[citation_for_row(row)],
        )

    return safe_refusal(
        "no_approved_evidence",
        "I cannot answer from score tables because the approved CSV evidence is unreadable.",
    )


def _answer_crown_surface_question(rows: list[FrozenEvidenceRow]) -> tuple[str, FrozenEvidenceRow] | None:
    for row in rows:
        if row.raw.get("relative_path") != "gm0518_kroonvolume_proxy_v1.csv":
            continue
        table = _read_table(row)
        if table is None:
            continue
        _fields, records = table
        for record in records:
            if _is_target_crown_surface_row(record):
                relative_path = str(row.raw.get("relative_path", Path(row.path).name))
                return synthesize_crown_surface_answer(relative_path, record), row
    return None


def _is_target_crown_surface_row(record: dict[str, str]) -> bool:
    return (
        record.get("aggregation_level") == "gemeente"
        and record.get("municipality_code") == "GM0518"
        and record.get("ahn_generation") == "AHN4"
        and record.get("acquisition_period") == "2020-2022"
    )


def _read_table(row: FrozenEvidenceRow) -> tuple[list[str], list[dict[str, str]]] | None:
    try:
        with Path(row.path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = [field for field in (reader.fieldnames or []) if field]
            records = [{key: item.get(key, "") for key in fields} for item in reader]
    except (OSError, csv.Error, UnicodeDecodeError):
        return None

    if not fields:
        return None
    return fields, records


def _is_crown_surface_question(question: str) -> bool:
    return bool(CROWN_SURFACE_RE.search(question) and THE_HAGUE_RE.search(question) and YEAR_2021_RE.search(question))


def _question_overlap(question: str, value: str) -> int:
    question_tokens = set(TOKEN_RE.findall(question.lower()))
    value_tokens = set(TOKEN_RE.findall(value.lower()))
    return len(question_tokens & value_tokens)
