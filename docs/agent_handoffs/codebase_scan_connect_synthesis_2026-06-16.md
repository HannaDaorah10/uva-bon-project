# Codebase Scan Handoff: connect-synthesis

Date: 2026-06-16
Branch confirmed with:

```bash
git -c safe.directory=/home/uva-bon/naturedesk/uva-bon-project -C /home/uva-bon/naturedesk/uva-bon-project status --short --branch
```

Observed output:

```text
## connect-synthesis...origin/connect-synthesis
```

Scope: internal/prototype only. No secrets were inspected or recorded. I did not call live Ollama, BON, web, GBIF, or external APIs. Application code was not edited.

## High-Level Flow

Current live assistant flow is:

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

Important distinction: `backend/server/synthesis.py` is the deterministic synthesis helper currently imported by the FastAPI handlers. `backend/synthesis/` is a separate prompt/prototype scaffold and is not the production server entry point.

## Important Files

- `backend/server/main.py`: FastAPI app, `/health`, `/api/query`, request/response models, handler dispatch, final citation validation.
- `backend/server/router_classifier.py`: local Qwen router contract, heuristic for The Hague crown-surface 2021 question, fail-closed classifier behavior.
- `backend/server/frozen_evidence.py`: frozen manifest gate, route requirements, readiness checks, denylist, allowed roots, checksum/readability checks, preflight export/action/official-claim refusals.
- `backend/server/frozen_evidence_manifest.json`: governed local evidence rows and readiness flags.
- `backend/server/citation_validator.py`: required citation fields and readiness requirements for any non-refusal answer.
- `backend/server/handlers/__init__.py`: `HandlerResponse`, approved-row lookup, citation construction.
- `backend/server/handlers/score_table.py`: approved CSV score-table handler; includes special crown-surface answer path.
- `backend/server/handlers/text_rag.py`: lexical JSONL chunk retrieval, max 3 chunks, chunk-level gates.
- `backend/server/handlers/map_raster.py`: STAC/catalog pointer handler only; no rendering or export.
- `backend/server/synthesis.py`: deterministic Markdown answer/refusal text helpers used by handlers.
- `frontend/bon-ui/src/App.tsx`: UI fetches `/api/query`, normalizes backend citations, renders answer/refusal states.
- `frontend/bon-ui/vite.config.ts`: dev proxy sends `/api` to `http://127.0.0.1:8000`.
- `backend/inputRouting/*`: standalone BON NDVI prompt-to-run prototype that calls local Ollama and BON. Keep separate from `/api/query` unless new gates are explicitly designed.
- `backend/synthesis/*`: standalone LLM/prompt synthesis scaffold. Useful for spec ideas, not wired into FastAPI.

## Route Contracts

Routes from `router_classifier.ROUTES`:

- `text_rag`: frozen text evidence. Manifest requirement is family `south_holland_student_retrieval`, type `text_chunk_export`. Handler reads JSONL, filters chunks where retrieve/quote are true and export/share/train are false, ranks by lexical token overlap, returns up to 3 chunks to deterministic text synthesis. Current manifest text row is not answer-facing ready, so this route should refuse until readiness changes.
- `score_table`: prepared score/indicator CSVs. Manifest requirement is family `kroonvolume_internal_proxy`, type `score_table`. Handler can return a preview for readable approved CSV rows. It also has a special deterministic answer for crown surface/kroonoppervlakte in The Hague/GM0518 at end of 2021, using `gm0518_kroonvolume_proxy_v1.csv`, AHN4, acquisition period `2020-2022`.
- `map_raster`: map/raster human-review pointer only. Manifest requirement is family `kroonvolume_internal_proxy`, type `map_raster_pointer`. Handler reads a JSON catalog/STAC-like artifact and returns a pointer, title/id, and link count. It does not render maps, export files, or infer ecology.
- `refusal`: safe refusal path from classifier or preflight.

Notable currently open answer-facing manifest rows include municipal/validation score tables and the v2 AHN5 STAC pointer. Many district/neighborhood/tile rows remain quote/citation/user-facing closed. Text retrieval remains closed.

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

`RouterDecision` keeps `explanation` internally, but `as_api_dict()` intentionally exposes only `route`, `refusalReason`, and `confidence`.

`EvidenceGateResult.as_api_dict()` exposes only `manifest_ids`, `missing_metadata`, and `blocked_gates`; `evidence_family` is copied onto `router` when present.

`HandlerResponse` is the handler boundary:

```text
refused: bool
answer: string
citations: list[dict]
refusal_reason?: string
```

For non-refusal answers, `citation_validator.py` requires each citation to include non-empty `manifest_id`, `citation`, `path`, `family`, and `type`, plus readiness where `retrieve_allowed`, `quote_allowed`, `citation_ready`, and `user_facing_ready` are true, and `export_allowed`, `share_external_llm_allowed`, and `train_allowed` are false.

Frontend `SynthesisResponse` only consumes `refused`, `answer`, `citations`, and `refusalReason`. It currently ignores backend `router` and `evidence` metadata. Frontend citation normalization maps backend fields like `manifest_id`, `citation`, `relative_path`, `family`, and `type` into display fields `id`, `title`, `source`, `artifactType`, and `locator`.

## Refusal and Readiness Behavior

The safest path is already enforced in this order:

1. `preflight_question_gate()` refuses before classification for export/archive/attach/download/bundle/source-index requests (`export_gate_required`), service/database/vector/evidence/pipeline mutation requests (`action_gate_required`), and official/municipal/validated/public-ready/client-ready/ecological-decision/management-action claims (`unsupported_claim`).
2. `classify_question()` refuses empty questions, model unavailability (`classifier_unavailable`), live/current data (`live_data_not_allowed`), legal/policy/high-stakes, unsupported causal/predictive claims, and out-of-scope/no-evidence requests.
3. `gate_query_evidence()` refuses unsupported routes, missing/bad manifests, no candidate rows, unreadable paths, denylisted paths, disallowed roots, checksum mismatch, missing metadata, or closed readiness.
4. Handlers refuse if approved rows are unavailable, unreadable, or no matching text chunks are retrieved.
5. `citations_are_valid()` is the last guardrail. Any non-refusal answer without valid citations becomes `citation_validation_failed`.

Do not loosen these gates to make demos appear to work. If evidence should become answer-facing, update the governed manifest/readiness package and tests together.

## Existing Tests

Backend tests live in `backend/server` and use `unittest`:

- `test_router_classifier.py`: route parsing, JSON extraction, fail-closed classifier behavior, heuristic crown-surface routing, API response shapes.
- `test_frozen_evidence.py`: preflight refusals, readiness/denylist/family separation, manifest loading, checksum behavior.
- `test_demo_handlers.py`: handler smoke tests, preflight order, live-data refusal, citation-validation failure.

Synthesis prototype checks live in `backend/synthesis`:

- `validate_response.py` and `validate_refusal.py` are hard-coded to sample Markdown files.
- `test_synthesis.py` is a manual/live OpenAI smoke test and should not be used in automated local verification without credentials and model/API review.

Frontend has Vite/TypeScript/ESLint scripts in `frontend/bon-ui/package.json`.

## Safe Extension Points

Recommended implementation path:

- Keep `/api/query` as the only UI-to-backend assistant endpoint unless a new contract is explicitly requested.
- Add server-side behavior inside `backend/server` modules first. Prefer extending `handlers/*`, `backend/server/synthesis.py`, and tests before touching frontend.
- Reuse `approved_rows_for_route()`, `citation_for_row()`, `HandlerResponse`, and `citations_are_valid()` for any new answer path.
- If adding a route, update all of: `ROUTES`, `ROUTER_SYSTEM_PROMPT`, `REFUSAL_REASONS` if needed, `ROUTE_REQUIREMENTS`, `HANDLERS`, citation mapping/tests, and frontend `toArtifactType()` if the UI needs a new badge.
- If exposing router/evidence details in the UI, extend `SynthesisResponse` in `App.tsx`; today those fields are silently ignored.
- Keep answer Markdown sections consistent with the current deterministic helpers: `## Answer`, `## Evidence used`, `## Uncertainty and gaps`, `## Assumptions`, `## Human review needed`, or `## Refusal`.

## What Not To Wire Yet

- Do not connect `backend/inputRouting/run_workflow.py` or `build_bon_json.py` into `/api/query`. They can call Ollama and BON, start runs, download outputs, and write run folders; that crosses action/export boundaries.
- Do not call live BON, GBIF, web, or external LLMs from the query path for this internal prototype unless new gates and tests are added.
- Do not use `backend/synthesis/test_synthesis.py` as production code. It is credential/model dependent and its inline prompt drifts from `synthesis_prompt.md`.
- Do not bypass manifest allowed roots, denylist, checksum, readiness, or citation validation.
- Do not return raw file exports, rendered maps, official/validated/public-ready/client-ready claims, municipal endorsements, ecological management actions, or unsupported causal explanations.
- Do not send evidence to an external LLM when `share_external_llm_allowed` is false.

## Verification Performed

From `backend/server`:

```bash
python3 -m unittest -v
```

Result: 33 tests passed.

From `frontend/bon-ui`:

```bash
npm run build
```

Result: failed before build output because TypeScript could not write cache files under `node_modules/.tmp`:

```text
TS5033: Could not write file .../node_modules/.tmp/tsconfig.app.tsbuildinfo: EACCES
TS5033: Could not write file .../node_modules/.tmp/tsconfig.node.tsbuildinfo: EACCES
```

No-emit checks that avoid the cache write passed:

```bash
./node_modules/.bin/tsc -p tsconfig.app.json --noEmit --incremental false
./node_modules/.bin/tsc -p tsconfig.node.json --noEmit --incremental false
npm run lint
```

## Suggested Next-Agent Plan

1. Start by deciding whether the goal is richer deterministic answers or route/metadata visibility in the UI. If backend answer behavior is the target, edit `backend/server/handlers/*`, `backend/server/synthesis.py`, and corresponding `backend/server/test_*.py` first.
2. Preserve the API response contract in `main.py`: `refused`, `answer`, `citations`, `refusalReason`, optional `router`, optional `evidence`.
3. Keep refusal-first behavior. Add tests for every new path that proves export/action/official/live/uncited cases still refuse.
4. If a readiness change is needed, treat it as a governed evidence-manifest decision, not a code workaround.
5. Re-run backend unit tests and frontend no-emit/lint. Use `npm run build` only after fixing `node_modules/.tmp` permissions or changing TS build-info output to a writable location.
