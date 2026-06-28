# NatureDesk UvA BON Prototype

This repository contains an internal student prototype for the UvA BON / NatureDesk challenge.

The project is a small web assistant for biodiversity and BON workflow questions. It is designed to answer only when it can use controlled local evidence. If the evidence is missing, unsafe, or not ready, the assistant should say that instead of guessing.

This project is not an official product, not public-ready, not client-ready, not municipal-endorsed, and not scientifically validated for final external claims.

## Who This Is For

This repo can help:

- students who want to try the NatureDesk assistant;
- reviewers who want to inspect how the prototype works;
- developers who need to change the frontend or backend;
- project members who need to understand the BON workflow helpers.

You do not need to know the whole codebase before trying it. Start with the launch steps below.

## What The Prototype Does

The assistant can:

- take a biodiversity or BON-related question in a web UI;
- send the question to a local FastAPI backend;
- route the question to the right evidence path;
- answer from approved local evidence when possible;
- show sources and trace information for supported answers;
- refuse questions that are outside scope, unsafe, live/current, unsupported, or not backed by approved evidence;
- answer from a file uploaded for the current session only, while clearly marking that answer as unverified.

The assistant should not:

- browse the live web during a question;
- query live GBIF during a question;
- export raw evidence bundles through chat;
- update services, databases, vectors, gates, or pipelines through chat;
- claim that NEO SignalEyes / Boombasis is ground truth;
- claim official Groenmonitor equivalence;
- claim municipal validation, public readiness, or client readiness.

## Main Repo Parts

```text
.
|-- frontend/
|   `-- bon-ui/              # React/Vite web UI
|-- backend/
|   |-- server/              # Active FastAPI assistant backend
|   |-- inputRouting/        # Standalone BON workflow wrappers
|   `-- synthesis/           # Older synthesis prototype material
|-- runtime_evidence/        # Local evidence files used by the backend manifest
`-- docs/
    `-- agent_handoffs/      # Handoff and scan notes
```

Read these files next for more detail:

- [Frontend overview](frontend/README.md)
- [UI app details](frontend/bon-ui/README.md)
- [Backend overview](backend/README.md)
- [Backend server details](backend/server/README.md)
- [BON workflow wrapper details](backend/inputRouting/README.md)
- [Older synthesis prototype notes](backend/synthesis/README.md)
- [Runtime evidence notes](runtime_evidence/README.md)
- [Documentation notes](docs/README.md)

## Full Launch Sequence

Use three terminals.

The SSH alias `uva-2yp` may be different on your machine. Use the alias that reaches the Spark machine where this project lives.

### Terminal 1: Start The Backend On Spark

```bash
ssh uva-2yp
cd ~/naturedesk/uva-bon-project/backend/server
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Leave this terminal open.

If `.venv` does not exist yet, create it first:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Terminal 2: Start The Frontend On Spark

```bash
ssh uva-2yp
cd ~/naturedesk/uva-bon-project/frontend/bon-ui
npm run dev -- --host 127.0.0.1 --port 5173
```

Confirm it prints a local URL like this:

```text
Local: http://127.0.0.1:5173/
```

Leave this terminal open.

### Terminal 3: Open The Tunnel From Your Laptop

Run this on your own laptop, not inside Spark:

```bash
ssh -L 5173:127.0.0.1:5173 uva-2yp
```

Leave this terminal open. It is normal that the prompt does not return.

### Browser

Open this on your laptop:

```text
http://127.0.0.1:5173/
```

You should see the NatureDesk assistant UI.

### Optional Backend Health Check

From any Spark terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected result:

```json
{"status":"ok"}
```

## How To Try The Assistant

1. Open the browser at `http://127.0.0.1:5173/`.
2. Type a biodiversity or BON question.
3. Choose a local model from the model menu if you want to test a different model.
4. Press Enter or click the search button.
5. Read the answer, refusal, sources, and trace tabs.

Good first questions:

```text
What evidence do we have about The Hague?
```

```text
What does the Kroonvolume proxy say about crown surface area in Den Haag?
```

```text
What information do we have about NEO SignalEyes Boombasis?
```

Expected behavior:

- If the backend has enough approved evidence, the UI shows an answer with sources.
- If the evidence is missing or unsafe, the UI shows a refusal with a reason.
- If you upload a file, the answer is only from that uploaded file and is marked unverified.

## How The Assistant Works

The normal request flow is:

```text
React UI
  -> POST /api/query
  -> preflight safety check
  -> router chooses a route
  -> evidence gate checks what is allowed
  -> route handler builds an answer or refusal
  -> citation validator checks the answer
  -> UI shows answer, sources, trace, or refusal
```

The active backend routes are:

- `workflow_rag`: broad controlled retrieval over the student baseline.
- `score_table`: prepared score or indicator tables.
- `map_raster`: approved map/raster pointers for human review.
- `text_rag`: older frozen text route, mostly closed unless gates allow it.
- `refusal`: clear refusal for unsupported or unsafe requests.

## Local Model Notes

The backend uses local Ollama models on Spark for routing and upload answers. The UI sends the selected model name to the backend.

Allowed model names currently include:

- `qwen2.5:7b`
- `qwen3.5:7b`
- `qwen3.5:14b`
- `llama3.1:8b`
- `mistral:7b`
- `gemma2:9b`
- `phi3:mini`

If a requested model is not allowed, the backend refuses the request.

## Common Commands

Run backend tests:

```bash
cd backend/server
python3 -m unittest -v
```

Build the frontend:

```bash
cd frontend/bon-ui
npm run build
```

Lint the frontend:

```bash
cd frontend/bon-ui
npm run lint
```

Check backend health:

```bash
curl http://127.0.0.1:8000/health
```

## Important Boundaries

The chat backend and the BON workflow scripts are different things.

The chat backend is the assistant API. It should answer or refuse from controlled evidence.

The files in `backend/inputRouting/` are standalone workflow wrappers. Some of them can start BON runs and write output files. Keep them separate from `/api/query` unless a new, reviewed action/export gate is designed.

Do not put secrets, credentials, raw restricted data, or external-release claims in README files, prompts, screenshots, or commits.
