# Codebase Scan Handoff: Neo_Bon_Workflow

Original date: 2026-06-16
Refreshed: 2026-06-18

Repo inspected: `/home/uva-bon/naturedesk/uva-bon-project`
Branch checked: `Neo_Bon_Workflow`
Branch head: `e7de688 Add safe local query understanding for workflow RAG`

Scope: internal/student prototype only. This is not public, client-ready, official, municipal-endorsed, or validated evidence. No secrets were inspected or recorded. This refresh updates documentation only.

## High-Level Flow

Current live assistant flow:

```text
frontend/bon-ui/src/App.tsx
  POST /api/query { question }
backend/server/main.py
  preflight_question_gate(question)
  classify_question(question)
  gate_query_evidence(route)
  HANDLERS[route](question, evidence_gate)
  citations_are_valid(result.citations)
  QueryResponse
```

Important distinction: `backend/server/synthesis.py` is the deterministic synthesis helper used by the active FastAPI handlers. `backend/synthesis/` is a separate older prompt/prototype scaffold and is not the current server entry point.

## Important Files

- `backend/server/main.py`: FastAPI app, `/health`, `/api/query`, request/response models, route dispatch, final citation validation.
- `backend/server/router_classifier.py`: route classifier, deterministic heuristics, local Qwen fallback, fail-closed parser.
- `backend/server/frozen_evidence.py`: frozen manifest gate, route requirements, readiness checks, allowed roots, denylist, checksum/readability checks, and preflight export/action/official/NEO claim refusals.
- `backend/server/frozen_evidence_manifest.json`: governed local evidence rows and readiness metadata.
- `backend/server/citation_validator.py`: final citation validation for frozen-manifest citations and retrieval-contract traces.
- `backend/server/handlers/__init__.py`: `HandlerResponse`, approved-row lookup, citation construction.
- `backend/server/handlers/score_table_dynamic.py`: active score-table handler imported by `main.py`.
- `backend/server/handlers/score_table.py`: older score-table handler retained in the repo.
- `backend/server/handlers/text_rag.py`: older lexical JSONL text route.
- `backend/server/handlers/workflow_rag.py`: controlled Diver/Curator retrieval-contract handler plus safe local query understanding for broad place-inventory questions.
- `backend/server/handlers/map_raster.py`: STAC/catalog pointer handler only; no rendering or export.
- `frontend/bon-ui/src/App.tsx`: UI fetches `/api/query`, normalizes backend citations, renders answer/refusal/source/trace states.
- `frontend/bon-ui/vite.config.ts`: dev proxy sends `/api` to `NATUREDESK_BACKEND_URL`, defaulting to `http://127.0.0.1:8001`, and uses a writable `/tmp` Vite cache.
- `backend/inputRouting/neo_workflow.py`: standalone NEO SignalEyes / Boombasis BON workflow wrapper. It is not wired into `/api/query`.
- `backend/inputRouting/run_workflow.py` and `build_bon_json.py`: older standalone BON/NDVI workflow helpers. Keep them out of the chat route unless a separate action/export gate is designed.

## Route Contracts

Routes from `router_classifier.ROUTES`:

- `workflow_rag`: controlled Diver/Curator retrieval over the combined student baseline. It covers IUCN Resolutions, BON in a Box student summaries, IUCN Red List CSV summaries, Kroonvolume Den Haag curated summaries, and governed NEO SignalEyes / Boombasis explainer chunks.
- `score_table`: prepared score/indicator CSVs from `kroonvolume_internal_proxy` rows. The active dynamic handler can answer The Hague/GM0518 crown-surface questions using the closest approved acquisition-period proxy and can otherwise return safe table previews.
- `map_raster`: map/raster human-review pointer only. It reads approved local catalog/STAC-like metadata and returns pointer fields, not rendered maps or exports.
- `text_rag`: older frozen JSONL text route. It remains mostly closed because current text rows are not answer-facing ready.
- `refusal`: safe refusal path from preflight, classifier, evidence gate, handler, or citation validator.

## Workflow RAG Query Plan

`workflow_rag` is no longer a pure literal-query pass-through. Its current plan is:

1. Detect known-place inventory questions for The Hague aliases: The Hague, Den Haag, 's-Gravenhage, gemeente Den Haag, and GM0518.
2. For broad inventory wording such as "What info do you have of The Hague?", try a fixed canonical retrieval query: `Den Haag The Hague Kroonvolume Groenmonitor NEO Boombasis urban biodiversity tree canopy evidence overview source holdings caveats`.
3. If deterministic recognition does not decide, optionally call local Ollama as a bounded query-understanding helper. The helper can only return `place_inventory` or `literal_retrieval` for a known place. It cannot answer, retrieve evidence, or invent a custom query.
4. Skip that helper for narrow or blocked topics such as current/live, mayor, weather, safety, policy, proof, official, validated, export, restart, or service/action requests.
5. Keep the literal user question as a fallback after the canonical query. The fallback is only tried if the canonical retrieval returns `insufficient_evidence`.
6. Do not retry after workflow unavailability, subprocess failure, invalid JSON, missing schemas, or other retrieval-contract failures.
7. NEO terms select `neo_den_haag_student_baseline` and default top-k 8. Other workflow questions use `student_combined_baseline` and default top-k 5.

Environment variables used by the route include:

```text
NATUREDESK_DIVER_CURATOR_WORKFLOW
NATUREDESK_RETRIEVAL_NAMESPACE
NATUREDESK_RETRIEVAL_TOP_K
NATUREDESK_RETRIEVAL_TIMEOUT_SECONDS
NATUREDESK_QUERY_UNDERSTANDING_LLM
NATUREDESK_QUERY_UNDERSTANDING_OLLAMA_URL
NATUREDESK_QUERY_UNDERSTANDING_MODEL
NATUREDESK_QUERY_UNDERSTANDING_TIMEOUT_SECONDS
```

## API Shapes

Backend request:

```json
{ "question": "..." }
```

Backend response model in `main.py`:

```text
refused: bool
answer: string
citations: list
refusalReason?: string
router?: { route, refusalReason, confidence, evidence_family? }
evidence?: { manifest_ids, missing_metadata, blocked_gates }
```

The frontend currently consumes `refused`, `answer`, `citations`, and `refusalReason`. It normalizes frozen-manifest citations and retrieval-contract traces into source cards and trace labels. It still does not expose the full backend `router` and `evidence` objects in a debug panel.

## Refusal And Readiness Behavior

The safest path is enforced in this order:

1. `preflight_question_gate()` refuses unsafe NEO framing, export/archive/download/bundle/source-index requests, service/database/vector/evidence/pipeline mutation requests, and official/municipal/validated/public-ready/client-ready/ecological-decision/management-action claims.
2. `classify_question()` refuses empty questions, classifier unavailability, live/current requests, legal/policy/high-stakes requests, unsupported causal/predictive claims, and out-of-scope/no-evidence requests.
3. `gate_query_evidence()` refuses unsupported routes, bad/missing manifests, no candidate rows, closed readiness gates, unreadable paths, denylisted paths, disallowed roots, checksum mismatch, or missing metadata. For `workflow_rag`, this stage allows the route through under the retrieval-contract boundary rather than a single manifest row.
4. Handlers refuse if approved rows or retrieval traces are unavailable, unreadable, weak-only, unsafe for internal answer use, or missing required fields.
5. `citations_are_valid()` is the last guardrail. Any non-refusal answer without valid citations becomes `citation_validation_failed`.

Do not loosen these gates for demo convenience. If evidence should become answer-facing, update the governed manifest/readiness package and tests together.

## Existing Tests

Backend tests live in `backend/server` and use `unittest`:

- `test_router_classifier.py`: route parsing, JSON extraction, fail-closed classifier behavior, heuristic routing, API response shapes.
- `test_frozen_evidence.py`: preflight refusals, NEO forbidden framing, readiness/denylist/family separation, manifest loading, checksum behavior, workflow contract gate.
- `test_demo_handlers.py`: handler smoke tests, workflow query planning, canonical The Hague inventory queries, local query-understanding fallback, literal fallback after insufficient evidence, preflight order, live-data refusal, and citation-validation failure.

Frontend has Vite/TypeScript build scripts in `frontend/bon-ui/package.json`.

## What Not To Wire Yet

- Do not connect `backend/inputRouting/neo_workflow.py`, `run_workflow.py`, or `build_bon_json.py` into `/api/query`. They can call Ollama and BON, start runs, download outputs, and write run folders.
- Do not call live BON, GBIF, web, or external LLMs from the query path unless new gates and tests are explicitly designed.
- Do not bypass manifest allowed roots, denylist, checksum, readiness, retrieval-contract trace checks, or citation validation.
- Do not return raw file exports, rendered maps, NEO raw feature dumps, credentials, official/validated/public-ready/client-ready claims, municipal endorsements, ecological management actions, or unsupported causal explanations.
- Do not send evidence to an external LLM when the relevant readiness/trace metadata blocks external sharing.

## Verification Performed

From `backend/server`:

```bash
python3 -m unittest -v
```

Result: 58 tests passed.

From `frontend/bon-ui`:

```bash
npm run build
```

Result: passed. Vite produced `dist/index.html`, `dist/assets/index-DyegyRLN.css`, and `dist/assets/index-Dj37FtY9.js`.

## Suggested Next-Agent Plan

1. Preserve `/api/query` as the governed assistant endpoint unless a new contract is explicitly requested.
2. If backend behavior changes, edit `backend/server` modules and tests first.
3. Keep refusal-first behavior and add tests for every new answer path.
4. If a readiness change is needed, treat it as an evidence-governance decision, not a code shortcut.
5. Add an internal UI debug drawer if students need route, confidence, evidence family, manifest IDs, blocked gates, and retrieval namespace visibility.
6. Add or document read-only PostgreSQL access for the runtime identity that runs the backend.
