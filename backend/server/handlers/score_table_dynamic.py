"""Safe retrieval handler for approved frozen score tables.

This module handles exact metric questions from structured CSV rows. Broad text
questions should use workflow_rag; numeric table questions should not be
answered by pgvector chunk summaries.
"""

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
from synthesis import synthesize_score_table_preview


TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
CROWN_SURFACE_RE = re.compile(
    r"(crown\s+surface|crown\s+area|tree\s+crown\s+area|kroonoppervlakte|kroon\s+oppervlakte)",
    re.IGNORECASE,
)
THE_HAGUE_RE = re.compile(r"(the\s+hague|den\s+haag|'s-gravenhage|gemeente\s+den\s+haag|gm0518)", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def handle_score_table(question: str, gate: EvidenceGateResult) -> HandlerResponse:
    rows = approved_rows_for_route("score_table", gate)
    if not rows:
        return concise_gate_refusal("score-table")

    if _is_crown_surface_question(question):
        crown_answer = _answer_crown_surface_question(question, rows)
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


def _answer_crown_surface_question(question: str, rows: list[FrozenEvidenceRow]) -> tuple[str, FrozenEvidenceRow] | None:
    requested_year = _requested_year(question)
    for row in rows:
        if row.raw.get("relative_path") != "gm0518_kroonvolume_proxy_v1.csv":
            continue
        table = _read_table(row)
        if table is None:
            continue
        _fields, records = table
        target = _select_crown_surface_row(records, requested_year)
        if target is None:
            continue
        record, match_note = target
        relative_path = str(row.raw.get("relative_path", Path(row.path).name))
        return _synthesize_crown_surface_answer(relative_path, record, requested_year, match_note), row
    return None


def _select_crown_surface_row(
    records: list[dict[str, str]],
    requested_year: int | None,
) -> tuple[dict[str, str], str] | None:
    candidates = [record for record in records if _is_municipality_crown_surface_row(record)]
    if not candidates:
        return None

    if requested_year is None:
        latest = max(candidates, key=lambda record: _period_sort_key(record.get("acquisition_period", "")))
        return latest, "No specific year was detected, so I used the latest AHN2/AHN3/AHN4 municipality proxy row."

    containing = [
        record
        for record in candidates
        if _period_contains_year(record.get("acquisition_period", ""), requested_year)
    ]
    if containing:
        record = max(containing, key=lambda item: _period_sort_key(item.get("acquisition_period", "")))
        return record, f"The requested year {requested_year} falls inside this AHN acquisition-period proxy label."

    closest = min(
        candidates,
        key=lambda record: _period_distance(record.get("acquisition_period", ""), requested_year),
    )
    return (
        closest,
        (
            f"No municipality proxy row directly covers {requested_year}; "
            "I used the closest available AHN acquisition-period proxy row."
        ),
    )


def _is_municipality_crown_surface_row(record: dict[str, str]) -> bool:
    return (
        record.get("aggregation_level") == "gemeente"
        and record.get("municipality_code") == "GM0518"
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
    return bool(CROWN_SURFACE_RE.search(question) and THE_HAGUE_RE.search(question))


def _requested_year(question: str) -> int | None:
    match = YEAR_RE.search(question)
    return int(match.group(1)) if match else None


def _period_bounds(period: str) -> tuple[int, int] | None:
    years = [int(value) for value in YEAR_RE.findall(period)]
    if len(years) < 2:
        return None
    return min(years), max(years)


def _period_contains_year(period: str, year: int) -> bool:
    bounds = _period_bounds(period)
    if bounds is None:
        return False
    start, end = bounds
    return start <= year <= end


def _period_distance(period: str, year: int) -> int:
    bounds = _period_bounds(period)
    if bounds is None:
        return 10_000
    start, end = bounds
    if start <= year <= end:
        return 0
    return min(abs(year - start), abs(year - end))


def _period_sort_key(period: str) -> tuple[int, int]:
    bounds = _period_bounds(period)
    return bounds if bounds is not None else (-1, -1)


def _question_overlap(question: str, value: str) -> int:
    question_tokens = set(TOKEN_RE.findall(question.lower()))
    value_tokens = set(TOKEN_RE.findall(value.lower()))
    return len(question_tokens & value_tokens)


def _synthesize_crown_surface_answer(
    relative_path: str,
    row: dict[str, str],
    requested_year: int | None,
    match_note: str,
) -> str:
    area_m2 = _format_decimal(row.get("candidate_area_m2", ""), decimals=2)
    area_ha = _format_decimal(row.get("candidate_area_ha", ""), decimals=6)
    acquisition_period = _clean(row.get("acquisition_period", "unknown acquisition period"))
    ahn_generation = _clean(row.get("ahn_generation", "unknown AHN generation"))
    unit_name = _clean(row.get("aggregation_unit_name", "GM0518 / The Hague"))
    uncertainty = _clean(row.get("uncertainty_class", "unknown"))
    caveats = _clean(row.get("caveat_flags", "not official; not validated"))
    year_phrase = f" for {requested_year}" if requested_year is not None else ""

    return f"""## Answer

I do not have an exact end-of-year measurement{year_phrase}. The approved municipality-level Kroonvolume proxy row that matches this question is {ahn_generation}, acquisition period {acquisition_period}, for {unit_name} / GM0518. In that row, candidate crown surface area is {area_m2} m2, or {area_ha} hectares. [1]

## Evidence used

| Source | Evidence |
|---|---|
| [1] `{relative_path}` | aggregation_level=gemeente; municipality_code=GM0518; ahn_generation={ahn_generation}; acquisition_period={acquisition_period}; candidate_area_m2={area_m2}; candidate_area_ha={area_ha}; uncertainty_class={uncertainty} |

## Important caveat

{match_note} This is an AHN acquisition-period proxy, not an official, validated, municipal, or exact calendar-date crown-surface measurement. Caveats on the row include: {caveats}.
"""


def _clean(value: object) -> str:
    return " ".join(str(value).split()) if value not in {None, ""} else "unknown"


def _format_decimal(value: object, decimals: int) -> str:
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return _clean(value)
    return f"{number:,.{decimals}f}"
