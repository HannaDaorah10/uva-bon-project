# NatureDesk Backend Server

This folder contains the active backend for the NatureDesk assistant.

It is a FastAPI server. The frontend sends questions here. The backend decides whether it can answer from controlled evidence or whether it must refuse.

## Start The Backend

From Spark:

```bash
cd ~/naturedesk/uva-bon-project/backend/server
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Leave the terminal open.

If `.venv` does not exist yet:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected result:

```json
{"status":"ok"}
```

## API Routes

### `GET /health`

Returns a simple health response.

### `POST /api/upload`

Accepts one temporary uploaded file.

The upload path is only for the current server process. It keeps extracted text in memory for a short time and marks the answer as unverified.

Supported file types:

```text
.yaml, .yml, .json, .jsonl, .md, .txt, .csv, .html, .pdf, .docx
```

### `POST /api/query`

Accepts a user question and returns either an answer or a refusal.

Request fields:

- `question`: required user question;
- `model`: optional local model name;
- `upload_id`: optional temporary upload id.

Response fields:

- `refused`: true or false;
- `answer`: answer or refusal text;
- `citations`: source traces;
- `refusalReason`: present for refusals;
- `router`: optional route metadata;
- `evidence`: optional evidence-gate metadata.

## Main Files

```text
main.py                         # FastAPI app and route dispatch
router_classifier.py            # Chooses the route for a question
frozen_evidence.py              # Checks evidence readiness and safety gates
frozen_evidence_manifest.json   # Approved local evidence rows
citation_validator.py           # Final citation check
scratch_upload.py               # Temporary uploaded-file path
synthesis.py                    # Deterministic answer text helpers
handlers/                       # Route-specific answer handlers
test_*.py                       # Unit tests
requirements.txt                # Python dependencies
```

## How A Normal Question Is Handled

```text
1. Receive POST /api/query.
2. If upload_id is present, use the separate scratch upload path.
3. Otherwise run preflight safety checks.
4. Validate the selected local model.
5. Classify the question into a route.
6. Check evidence gates for that route.
7. Run the selected handler.
8. Validate citations.
9. Return an answer or refusal.
```

## Routes

### `workflow_rag`

For broad retrieval questions over the controlled student baseline.

It can cover topics such as IUCN, BON in a Box, IUCN Red List summaries, Kroonvolume Den Haag summaries, and NEO SignalEyes / Boombasis explainer material.

It depends on the controlled Diver/Curator workflow and refuses if the workflow is missing, weak, invalid, or unsafe.

### `score_table`

For prepared score or indicator tables.

Example: a The Hague / Den Haag / GM0518 crown surface area question can use approved Kroonvolume proxy CSV rows.

### `map_raster`

For approved map or raster pointers.

This route can point to approved catalog metadata for human review. It does not export or render raw map data through chat.

### `text_rag`

Older frozen text route. It remains conservative and may refuse unless its evidence gates are open.

### `refusal`

Used when the request is outside scope, unsafe, unsupported, live/current, policy-restricted, missing evidence, or blocked by readiness gates.

## Local Model Allowlist

The backend only accepts selected local model names.

Allowed names:

- `qwen2.5:7b`
- `qwen3.5:7b`
- `qwen3.5:14b`
- `llama3.1:8b`
- `mistral:7b`
- `gemma2:9b`
- `phi3:mini`

If the UI or caller sends another model name, the backend refuses with `invalid_model`.

## Important Safety Gates

The backend refuses requests for:

- live or current data;
- unsupported causal or predictive claims;
- legal, policy, or high-stakes advice;
- export, archive, download, bundle, or source-index requests;
- update, install, restart, rerun, database, vector, service, evidence, or pipeline mutation requests;
- official, municipal, validated, public-ready, client-ready, ecological-decision, or management-action claims;
- unsafe NEO framing such as ground truth, proof, official alignment, municipal equivalence, or Groenmonitor equivalence.

These refusals are intentional.

## Environment Variables

The workflow route can use these variables:

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

Defaults are set in `handlers/workflow_rag.py`.

## Tests

Run the backend test suite:

```bash
cd backend/server
python3 -m unittest -v
```

The tests are important because many backend behaviors are safety boundaries, not just convenience features.

## Common Problems

If `/health` fails, the backend is not running or is on another port.

If the UI cannot reach the backend, check the Vite proxy and make sure the backend is on `127.0.0.1:8000`.

If `workflow_rag` refuses, check that the Diver/Curator workflow, local Ollama, and local retrieval database are reachable by the user running the backend.

If a question should answer but refuses, do not bypass the gate in code. Check the manifest, evidence readiness, citations, and tests.
