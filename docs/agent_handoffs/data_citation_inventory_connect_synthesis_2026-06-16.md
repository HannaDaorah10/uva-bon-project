# Data And Citation Inventory: Neo_Bon_Workflow

Original date: 2026-06-16
Refreshed: 2026-06-18

Branch checked: `Neo_Bon_Workflow`.
Current branch head: `e7de688 Add safe local query understanding for workflow RAG`.

Scope: internal/student prototype only. This file records availability and gates; it does not promote any source to public, client, official, export, external-LLM, or training use.

## Current Assistant-Usable Data

The frozen manifest is `backend/server/frozen_evidence_manifest.json`.

It has 64 rows across these families:

- `kroonvolume_internal_proxy`
- `south_holland_student_retrieval`
- `prototype_proof`
- `method_context`

Only 5 frozen-manifest rows currently pass the strict answer/citation gates:

- `kroonvolume_v1_gm0518_kroonvolume_proxy_v1_csv`
- `kroonvolume_v1_uncertainty_register_v1_csv`
- `kroonvolume_v2_ahn5_gm0518_kroonvolume_proxy_v2_csv`
- `kroonvolume_v2_ahn5_validation_readiness_matrix_v2_csv`
- `kroonvolume_v2_stac_collection_json`

Those rows are internal prototype evidence only. They keep `export_allowed=false`, `share_external_llm_allowed=false`, and `train_allowed=false`.

## New Broad Retrieval Route

The backend now has a separate `workflow_rag` route for Platypus-style broad retrieval.

It calls the controlled Diver/Curator workflow:

```text
/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py
```

Default namespace:

```text
student_combined_baseline
```

That combined namespace is the broad source surface currently wired to the assistant:

- IUCN Resolutions pgvector baseline
- BON in a Box student baseline summaries
- IUCN Red List CSV student baseline summaries
- Kroonvolume Den Haag curated summary baseline
- NEO SignalEyes / Boombasis Den Haag explainer-chunk baseline

NEO-specific questions are routed to `neo_den_haag_student_baseline` by the backend handler so the assistant searches the 8 approved NEO explainer chunks instead of diluting them with unrelated Den Haag evidence. The NEO namespace exposes only explainer chunks and controlled provenance references, not raw GeoJSON, credentials, feature-level exports, or direct `neo_features`/`neo_comparison_rows` dumps.

The route uses `retrieval_package.v1` plus `source_assessment.v1`. It answers only from chunks assessed as strong/moderate or usable/partial, with source traces. It refuses on workflow failure, insufficient evidence, weak-only evidence, missing trace fields, unsafe NEO validation/equivalence framing, or external/training gate problems.

Current retrieval-query behavior:

- Literal user wording is not always the first and only retrieval string.
- Broad The Hague / Den Haag / 's-Gravenhage / GM0518 inventory questions are canonicalized to a fixed Den Haag evidence-overview query covering Kroonvolume, Groenmonitor, NEO, Boombasis, urban biodiversity, tree canopy evidence, source holdings, and caveats.
- The literal user question remains as a fallback only after canonical retrieval returns `insufficient_evidence`.
- The fallback is not used after workflow unavailability, subprocess failure, invalid JSON, missing schemas, or other contract failures.
- A bounded local Ollama helper can classify `place_inventory` versus `literal_retrieval` for known-place questions. It cannot answer the user, retrieve evidence, or create custom search text, and it is skipped for blocked/narrow wording such as live/current, mayor, weather, policy, proof, official, validated, export, restart, or action requests.

## Visible But Blocked Data

These files or rows are visible but should not be treated as answer-ready just because they exist:

- South Holland JSONL/text retrieval rows: current manifest gates are closed for quote/citation/user-facing answer use.
- Kroonvolume stadsdeel/wijk/buurt/tile rows: visible in release folders, but not all are answer-ready in the manifest.
- Prototype proof files and stress reports: useful as process evidence, not answer evidence.
- Method-context YAML files: visible, but answer gates remain closed.
- `backend/inputRouting/runs/*`: BON/NDVI run artifacts from a standalone workflow path; not governed by `/api/query` answer gates.
- `backend/synthesis/*`: prompt/prototype synthesis material; not the active server synthesis path.
- Raw NEO feature payloads, feature-level database exports, query dumps, and raw coordinates remain outside assistant answer/export scope. The assistant may cite the local NEO dataset source-of-truth baseline under licence through the governed explainer traces only.

## Remaining Runtime Caveat

The workflow file is now traversable/readable for the `uva-bon` Linux user, and the metadata-only workflow log is writable.

The remaining Spark wiring weak point is PostgreSQL authentication: the local `biodiversity` database currently exposes roles for `hans` and `postgres`, but no confirmed `uva-bon` DB role was found from this session. If the backend is run as `uva-bon`, the broad `workflow_rag` route may refuse because the pgvector query cannot authenticate. Fix with a read-only DB role/authentication rule, or run the backend under an OS/DB identity already allowed to query the approved pgvector mirrors.

## Do Not Do

- Do not mass-promote manifest rows.
- Do not bypass `citation_validator.py`.
- Do not connect `backend/inputRouting/run_workflow.py` or live BON execution into `/api/query`.
- Do not use raw filesystem search as a fallback for answer evidence.
- Do not send chunks to external LLMs while `share_with_external_llm=false`.
- Do not claim public/client/official/validated/municipal readiness.
- Do not frame NEO as ground truth, proof, official alignment, municipal equivalence, or Groenmonitor equivalence.

## Verification Snapshot

From the current runtime:

- Backend unit tests: `python3 -m unittest -v` passed, 58 tests.
- Frontend type checks and lint passed.
- Frontend build passed with `npm run build`.
- API smoke: IUCN indigenous/protected-area question routed to `workflow_rag`, returned `refused=false` with 5 source traces.
- API smoke: NEO SignalEyes / Boombasis Den Haag question routed to `workflow_rag`, returned `refused=false` with a `neo_den_haag_student_baseline` source trace.
- API smoke: NEO ground-truth/proof/Groenmonitor-equivalence question refused with `unsupported_claim` and `neo_validation_or_equivalence_claim`.
- API smoke: The Hague crown-surface 2021 question routed to `score_table`, returned `refused=false` with 1 frozen-manifest citation.
- API smoke: official/validated/public-ready claim refused with `unsupported_claim`.
