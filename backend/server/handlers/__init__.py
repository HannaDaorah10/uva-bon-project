"""Shared utilities for minimal safe demo handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from frozen_evidence import (
    EvidenceGateResult,
    FrozenEvidenceError,
    FrozenEvidenceIndex,
    FrozenEvidenceRow,
    ROUTE_REQUIREMENTS,
    validate_row,
)


@dataclass(frozen=True)
class HandlerResponse:
    refused: bool
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    refusal_reason: str | None = None


def safe_refusal(refusal_reason: str, answer: str) -> HandlerResponse:
    return HandlerResponse(
        refused=True,
        answer=answer,
        citations=[],
        refusal_reason=refusal_reason,
    )


def approved_rows_for_route(route: str, gate: EvidenceGateResult) -> list[FrozenEvidenceRow]:
    """Return rows that passed the manifest gate and remain locally readable."""
    requirements = ROUTE_REQUIREMENTS.get(route)
    if requirements is None or gate.refused or not gate.manifest_ids:
        return []

    approved_ids = set(gate.manifest_ids)
    try:
        index = FrozenEvidenceIndex.load()
    except FrozenEvidenceError:
        return []

    rows: list[FrozenEvidenceRow] = []
    for row in index.rows:
        if row.row_id not in approved_ids:
            continue
        if row.family not in requirements["families"]:
            continue
        if row.row_type not in requirements["types"]:
            continue
        missing, blocked = validate_row(row)
        if not missing and not blocked:
            rows.append(row)
    return rows


def citation_for_row(row: FrozenEvidenceRow) -> dict[str, Any]:
    return {
        "manifest_id": row.row_id,
        "citation": str(row.raw.get("citation", "")),
        "path": row.path,
        "relative_path": str(row.raw.get("relative_path", Path(row.path).name)),
        "family": row.family,
        "type": row.row_type,
        "readiness": row.readiness,
        "requires_human_review": bool(row.raw.get("requires_human_review", True)),
        "caveat_flags": list(row.raw.get("caveat_flags") or []),
    }


def concise_gate_refusal(route_label: str) -> HandlerResponse:
    return safe_refusal(
        "no_approved_evidence",
        (
            f"I cannot answer this {route_label} request because no approved, "
            "readable frozen evidence row is available to the backend."
        ),
    )


def truncate(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def route_caveat_sentence() -> str:
    return (
        "This is internal student/prototype evidence only; it is not official, "
        "validated, public-ready, client-ready, or approved for export."
    )
