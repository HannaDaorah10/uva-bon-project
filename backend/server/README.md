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

The route classifier, frozen evidence gate, and minimal demo handlers are connected.

That means:

- If the classifier chooses `refusal`, the API returns a domain refusal.
- If a route has no approved readable evidence, the API refuses before a handler runs.
- If approved evidence is readable but answer-facing readiness is closed, the API refuses with `readiness_gate_blocked`.
- If future manifest rows open the required readiness gates, the score-table and map/raster demo handlers can return small cited previews or pointers.
- `text_rag` still refuses factual synthesis until retrieval and synthesis are implemented.
- Every response keeps the frontend fields `refused`, `answer`, `citations`, and `refusalReason`. Router details are exposed only in the optional `router` object.

This is intentional. It lets the frontend and backend route meet without returning fake evidence or bypassing the frozen evidence gates.

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

With the current manifest, answer-facing readiness gates are closed, so live route questions should refuse rather than expose factual evidence previews. To return demo answers, update the governed manifest/readiness package first, then keep citation validation and handler tests aligned with those gates.
