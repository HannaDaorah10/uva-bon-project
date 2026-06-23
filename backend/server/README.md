# NatureDesk backend server

Minimal FastAPI HTTP surface for the NatureDesk query router.

## Run

```bash
cd backend/server
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The router classifier and workflow query-understanding fallback use a local Spark Ollama model selected from the backend allowlist:

```text
default: qwen2.5:7b at http://127.0.0.1:11434/api/generate
allowed: qwen2.5:7b, qwen3.5:7b, qwen3.5:14b, llama3.1:8b, mistral:7b, gemma2:9b, phi3:mini
```

The endpoint is fixed to the local Ollama boundary. The request model tag is validated against the allowlist before it can reach Ollama.

## Routes

- `GET /health` returns a basic service status.
- `POST /api/query` accepts JSON with `question: string` and optional `model: string`, then returns the frontend response shape.

## Router classification

`POST /api/query` now calls the local Qwen router classifier first. It asks Qwen to choose one route:

- `text_rag`
- `workflow_rag`
- `score_table`
- `map_raster`
- `refusal`

The classifier must refuse legal/policy/high-stakes questions, live/current data requests, unsupported causal/predictive claims, and questions that cannot be grounded in the frozen prepared evidence boundary.

## Current behavior

The route classifier, frozen evidence gate, and minimal demo handlers are connected.

That means:

- If the classifier chooses `refusal`, the API returns a domain refusal.
- If a route has no approved readable evidence, the API refuses before a handler runs.
- If approved evidence is readable but answer-facing readiness is closed, the API refuses with `readiness_gate_blocked`.
- `score_table` can answer from approved Kroonvolume CSV rows after manifest/citation gates pass.
- `map_raster` can return approved map/raster pointers for human review only.
- `workflow_rag` calls the controlled Diver/Curator workflow and answers only from `retrieval_package.v1` chunks assessed by `source_assessment.v1` as strong/moderate or usable/partial.
- `text_rag` remains the older manifest-bound JSONL route and still refuses unless its row and chunk gates open.
- Every response keeps the frontend fields `refused`, `answer`, `citations`, and `refusalReason`. Router details are exposed only in the optional `router` object.

This is intentional. It lets the frontend and backend route meet without returning fake evidence or bypassing the frozen evidence gates.

## Diver/Curator workflow route

`workflow_rag` is the Platypus-style broad retrieval route. It defaults to:

```text
NATUREDESK_DIVER_CURATOR_WORKFLOW=/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py
NATUREDESK_RETRIEVAL_NAMESPACE=student_combined_baseline
NATUREDESK_RETRIEVAL_TOP_K=5
NATUREDESK_RETRIEVAL_TIMEOUT_SECONDS=75
```

The combined namespace includes IUCN Resolutions, BON in a Box student summaries, IUCN Red List CSV summaries, and Kroonvolume Den Haag curated summaries, as configured by the shared Diver/Curator workflow.

The route fails closed when:

- the workflow path is unreadable or unavailable;
- Ollama or pgvector retrieval fails;
- the workflow does not return both required schemas;
- Curator/source assessment says evidence is insufficient;
- no strong/moderate or usable/partial source trace is available;
- a chunk is missing trace fields or opens external-LLM/training use.

Important runtime caveat: if this backend is run as Linux user `uva-bon`, the workflow file is now traversable/readable, but the local PostgreSQL `biodiversity` database may still need a read-only role or authentication rule for that user. If the DB role is missing, the route should refuse through the retrieval contract instead of falling back to raw files.

## Test

The unit tests do not require live Ollama:

```bash
cd backend/server
python3 -m unittest -v
```

## Frozen evidence manifest

`POST /api/query` now enforces a frozen local evidence manifest before any future retrieval handler can run. The manifest is `backend/server/frozen_evidence_manifest.json`.

The gate is intentionally fail-closed:

- source families are separated by route: South Holland controlled JSONL only for `text_rag`, Kroonvolume score tables only for `score_table`, and Kroonvolume raster/catalog pointers only for `map_raster`.
- missing readiness fields, closed readiness gates, denied paths, missing files, unreadable files, and checksum mismatches refuse.
- export/archive/attach/bundle requests refuse with `export_gate_required`.
- update/install/restart/rerun/service/database/vector/evidence-gate mutation requests refuse with `action_gate_required`.
- official, municipal, validated, public-ready, client-ready, legal, ecological decision, or management-action claims refuse with `unsupported_claim`.

Current Spark runtime caveat: several approved evidence paths are under `/home/hans/.openclaw/...`; if the backend process cannot read those files, `/api/query` returns `no_approved_evidence` or `retrieval_contract_unavailable` instead of proceeding.

Do not mass-open manifest rows to broaden answers. To make more local files answer-facing, update the governed manifest/readiness package first, then keep citation validation and handler tests aligned with those gates.
