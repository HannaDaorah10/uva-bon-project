# Data And Citation Inventory: connect-synthesis

Date: 2026-06-16

Branch checked: `connect-synthesis`.

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

The route uses `retrieval_package.v1` plus `source_assessment.v1`. It answers only from chunks assessed as strong/moderate or usable/partial, with source traces. It refuses on workflow failure, insufficient evidence, weak-only evidence, missing trace fields, or external/training gate problems.

## Visible But Blocked Data

These files or rows are visible but should not be treated as answer-ready just because they exist:

- South Holland JSONL/text retrieval rows: current manifest gates are closed for quote/citation/user-facing answer use.
- Kroonvolume stadsdeel/wijk/buurt/tile rows: visible in release folders, but not all are answer-ready in the manifest.
- Prototype proof files and stress reports: useful as process evidence, not answer evidence.
- Method-context YAML files: visible, but answer gates remain closed.
- `backend/inputRouting/runs/*`: BON/NDVI run artifacts from a standalone workflow path; not governed by `/api/query` answer gates.
- `backend/synthesis/*`: prompt/prototype synthesis material; not the active server synthesis path.

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

## Verification Snapshot

From the current runtime:

- Backend unit tests: `python3 -m unittest -v` passed, 39 tests.
- Frontend type checks and lint passed.
- Frontend build passed after repairing local generated-cache/output ACLs.
- API smoke: IUCN indigenous/protected-area question routed to `workflow_rag`, returned `refused=false` with 5 source traces.
- API smoke: The Hague crown-surface 2021 question routed to `score_table`, returned `refused=false` with 1 frozen-manifest citation.
- API smoke: official/validated/public-ready claim refused with `unsupported_claim`.
