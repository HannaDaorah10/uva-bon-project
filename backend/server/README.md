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

The router classifier uses the local Spark Ollama model:

```text
qwen2.5:7b at http://127.0.0.1:11434/api/generate
```

The model and endpoint are fixed in code to preserve the local-only architecture boundary.

## Routes

- `GET /health` returns a basic service status.
- `POST /api/query` accepts JSON with `question: string` and returns the frontend response shape.

## Router classification

`POST /api/query` now calls the local Qwen router classifier first. It asks Qwen to choose one route:

- `text_rag`
- `score_table`
- `map_raster`
- `refusal`

The classifier must refuse legal/policy/high-stakes questions, live/current data requests, unsupported causal/predictive claims, and questions that cannot be grounded in the frozen prepared evidence boundary.

## Current behavior

The route classifier is connected. Retrieval and synthesis are not connected yet.

That means:

- If the classifier chooses `refusal`, the API returns a domain refusal.
- If the classifier chooses `text_rag`, `score_table`, or `map_raster`, the API still fails closed with `refusalReason: backend_pipeline_not_connected`.
- Every response keeps the frontend fields `refused`, `answer`, `citations`, and `refusalReason`. Router details are exposed only in the optional `router` object.

This is intentional. It lets the frontend and backend route meet without returning fake evidence.

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

Current Spark runtime caveat: the approved evidence paths are under `/home/hans/.openclaw/...`; if the `uva-bon` backend process cannot read those files, `/api/query` returns `no_approved_evidence` instead of proceeding.

Even when a route has valid approved manifest rows, the API still returns `backend_pipeline_not_connected` until retrieval handlers, citation validation, and synthesis are connected.
