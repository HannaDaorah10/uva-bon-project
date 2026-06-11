"""Deterministic synthesis helpers for approved frozen evidence.

These helpers do not call BON in a Box, LLMs, live APIs, web services, or
external tools. They only turn already-approved retrieved evidence into short
answers with traceable citations and caveats.
"""

from __future__ import annotations

from typing import Any


def synthesize_crown_surface_answer(relative_path: str, row: dict[str, str]) -> str:
    area_m2 = _format_decimal(row.get("candidate_area_m2", ""), decimals=2)
    area_ha = _format_decimal(row.get("candidate_area_ha", ""), decimals=6)
    acquisition_period = _clean(row.get("acquisition_period", "unknown acquisition period"))
    ahn_generation = _clean(row.get("ahn_generation", "unknown AHN generation"))
    unit_name = _clean(row.get("aggregation_unit_name", "GM0518 / The Hague"))
    uncertainty = _clean(row.get("uncertainty_class", "unknown"))
    readiness = _clean(row.get("readiness_label", "internal prototype evidence"))
    caveats = _clean(row.get("caveat_flags", "not official; not validated"))

    return f"""## Answer

The frozen Kroonvolume evidence does not contain an exact measurement for the end of 2021. The closest approved municipality-level proxy row is {ahn_generation}, acquisition period {acquisition_period}, for {unit_name} / GM0518. In that row, the candidate crown surface area is {area_m2} m2, which is {area_ha} hectares. This is an internal prototype value, not an official or validated municipal figure. [1]

## Evidence used

| Source | Evidence |
|---|---|
| [1] `{relative_path}` | aggregation_level=gemeente; municipality_code=GM0518; ahn_generation={ahn_generation}; acquisition_period={acquisition_period}; candidate_area_m2={area_m2}; candidate_area_ha={area_ha}; uncertainty_class={uncertainty} |

## Uncertainty and gaps

The date wording matters. The table labels this as an AHN acquisition-period proxy, not as an exact value on 31 December 2021. The row also carries caveats: {caveats}.

## Assumptions

I interpreted "crown surface area" / "kroonoppervlakte" as the table field `candidate_area_m2` / `candidate_area_ha`, and "municipality of The Hague" as GM0518 / 's-Gravenhage. I used the {acquisition_period} row because it is the closest available row covering 2021.

## Human review needed

Before using this outside the demo, a human should verify that `candidate_area_m2` is the intended crown-surface metric and confirm whether an AHN acquisition-period proxy is acceptable for the question.

Readiness note: {readiness}. {route_caveat_sentence()}
"""


def synthesize_score_table_preview(
    relative_path: str,
    fields: list[str],
    first_row: dict[str, str],
    row_count: int,
) -> str:
    shown_fields = ", ".join(fields[:8])
    shown_cells = "; ".join(
        f"{field}={truncate(first_row.get(field, ''), 80)}" for field in fields[:6]
    )
    return f"""## Answer

Approved score-table evidence is readable: `{relative_path}`. Rows detected: {row_count}. Columns include: {shown_fields}. First available row preview: {shown_cells}. [1]

## Evidence used

| Source | Evidence |
|---|---|
| [1] `{relative_path}` | Readable approved score-table row preview from the frozen manifest. |

## Uncertainty and gaps

This is a table preview, not a full ecological interpretation.

## Assumptions

I treated the best matching approved table as the relevant source for this question.

## Human review needed

A human should inspect the selected row and confirm the metric interpretation before external use. {route_caveat_sentence()}
"""


def synthesize_map_raster_pointer(
    relative_path: str,
    collection_id: str,
    title: str,
    item_count: int,
) -> str:
    return f"""## Answer

Approved map/raster pointer available for human review: `{relative_path}`. Catalog id/title: {collection_id} / {title}. Catalog link count: {item_count}. I am not exporting files, rendering a map, calling live services, or making new ecological conclusions. [1]

## Evidence used

| Source | Evidence |
|---|---|
| [1] `{relative_path}` | Approved frozen manifest map/raster pointer. |

## Uncertainty and gaps

This is a pointer to a local catalog, not a rendered map or ecological conclusion.

## Assumptions

I treated the catalog metadata as a human-review pointer only.

## Human review needed

A human should open the local catalog/raster package and verify the visual evidence before use. {route_caveat_sentence()}
"""


def synthesize_text_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return """## Refusal

I cannot answer from the approved text evidence.

Reason:
No matching approved text chunks were retrieved.

What a human should consult instead:
The frozen evidence manifest and source package.
"""

    evidence_rows = []
    answer_parts = []
    for index, chunk in enumerate(chunks, start=1):
        title = truncate(chunk.get("title", "approved text chunk"), 100)
        text = truncate(_chunk_text(chunk), 240)
        chunk_id = truncate(chunk.get("chunk_id", f"chunk-{index}"), 80)
        citation = truncate(chunk.get("citation_string", "Frozen text evidence"), 140)
        evidence_rows.append(f"| [{index}] {title} | chunk_id={chunk_id}; citation={citation}; relevant text={text} |")
        answer_parts.append(f"{text} [{index}]")

    return f"""## Answer

The approved text retrieval found {len(chunks)} relevant chunk(s) for the question: {question}. {' '.join(answer_parts)}

## Evidence used

| Source | Evidence |
|---|---|
{chr(10).join(evidence_rows)}

## Uncertainty and gaps

This answer is based only on lexical retrieval over the approved frozen JSONL text package. It may miss relevant chunks if the wording differs.

## Assumptions

I used only chunks whose row-level metadata allows retrieval and quotation, and I did not use model memory or live sources.

## Human review needed

A human should verify the selected chunks and citations before using the answer outside the demo. {route_caveat_sentence()}
"""


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


def _chunk_text(chunk: dict[str, Any]) -> str:
    for field in ("text", "chunk_text", "content", "body", "preview"):
        value = chunk.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _clean(value: Any) -> str:
    return " ".join(str(value).split()) if value not in {None, ""} else "unknown"


def _format_decimal(value: Any, decimals: int) -> str:
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return _clean(value)
    return f"{number:,.{decimals}f}"
