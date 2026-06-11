# NatureDesk backend server skeleton

Minimal FastAPI HTTP surface for frontend integration checks.

## Run

```bash
cd backend/server
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Routes

- `GET /health` returns a basic service status.
- `POST /api/query` accepts JSON with `question: string` and returns the frontend response shape.

`POST /api/query` currently fails closed with `refused: true` and `refusalReason: backend_pipeline_not_connected` because input routing, retrieval, and synthesis are not wired into this HTTP service yet.
