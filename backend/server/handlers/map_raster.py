"""Safe pointer handler for approved map/raster artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from frozen_evidence import EvidenceGateResult
from handlers import (
    HandlerResponse,
    approved_rows_for_route,
    citation_for_row,
    concise_gate_refusal,
    route_caveat_sentence,
    safe_refusal,
    truncate,
)


def handle_map_raster(question: str, gate: EvidenceGateResult) -> HandlerResponse:
    rows = approved_rows_for_route("map_raster", gate)
    if not rows:
        return concise_gate_refusal("map/raster")

    row = rows[0]
    try:
        payload = json.loads(Path(row.path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return safe_refusal(
            "no_approved_evidence",
            "I cannot provide a map/raster pointer because the approved artifact is unreadable.",
        )

    collection_id = truncate(payload.get("id", "approved raster catalog"), 80)
    title = truncate((payload.get("title") or payload.get("description") or collection_id), 160)
    item_count = len(payload.get("links") or []) if isinstance(payload.get("links"), list) else 0
    relative_path = str(row.raw.get("relative_path", Path(row.path).name))

    answer = (
        f"Approved map/raster pointer available for human review: `{relative_path}`. "
        f"Catalog id/title: {collection_id} / {title}. "
        f"Catalog link count: {item_count}. "
        "I am not exporting files, rendering a map, calling live services, or making "
        f"new ecological conclusions. {route_caveat_sentence()}"
    )

    return HandlerResponse(
        refused=False,
        answer=answer,
        citations=[citation_for_row(row)],
    )
