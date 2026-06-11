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
