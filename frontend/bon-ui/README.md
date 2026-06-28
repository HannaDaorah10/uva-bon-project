# NatureDesk UI

This folder contains the browser app for the NatureDesk assistant.

It is a React, TypeScript, and Vite app. It talks to the backend through `/api/query` and `/api/upload`.

## What Users See

The UI has:

- a NatureDesk wordmark;
- a local model menu;
- an upload button;
- a question box;
- an output panel;
- tabs for answer, sources, and trace details.

The UI is meant to make backend behavior visible. If the backend refuses, the UI shows the refusal and the reason. If the backend answers, the UI shows the answer and the source traces.

## Start The UI

From Spark:

```bash
cd ~/naturedesk/uva-bon-project/frontend/bon-ui
npm run dev -- --host 127.0.0.1 --port 5173
```

Then open the tunnel from your laptop:

```bash
ssh -L 5173:127.0.0.1:5173 uva-2yp
```

Open:

```text
http://127.0.0.1:5173/
```

The SSH alias may be different on your machine.

## Main Files

```text
src/App.tsx       # Main component, API calls, model menu, upload, output tabs
src/App.css       # Layout, colors, typography, responsive UI styling
src/main.tsx      # Mounts the React app
vite.config.ts    # Dev server config and API proxy
package.json      # Scripts and dependencies
public/           # Static assets
```

## API Contract Used By The UI

The UI sends:

- `question`: the text typed by the user;
- `model`: the selected local model name;
- `upload_id`: only when a file was uploaded first.

The UI expects either a supported answer or a refusal.

Supported answer fields:

- `refused`: false;
- `answer`: answer text;
- `citations`: source trace list.

Refusal fields:

- `refused`: true;
- `answer`: refusal text;
- `citations`: usually empty;
- `refusalReason`: machine-readable refusal reason.

The backend may also return `router` and `evidence` fields. The current UI mainly displays the answer, refusal, citations, and trace labels.

## Model Menu

The model menu sends one allowed Ollama model name to the backend. The backend still validates the model name. The UI is not the safety boundary.

Current model choices shown in the UI:

- `qwen2.5:7b`
- `qwen3.5:7b`
- `qwen3.5:14b`
- `llama3.1:8b`
- `mistral:7b`
- `gemma2:9b`
- `phi3:mini`

## Upload Button

The upload feature is for quick testing.

What happens:

1. The user picks a file.
2. The UI sends it to `POST /api/upload`.
3. The backend returns an upload id.
4. The next question includes that upload id.
5. The backend answers only from that uploaded file.

Important: uploaded-file answers are unverified. They are not approved NatureDesk evidence.

Supported upload types are controlled by the backend, but the UI currently accepts:

```text
.yaml, .yml, .json, .jsonl, .md, .txt, .csv, .html, .pdf, .docx
```

## Output States

The UI handles five states:

- `idle`: no question has been asked yet;
- `loading`: the backend is working;
- `answer`: the backend returned a supported answer;
- `refusal`: the backend refused with a reason;
- `error`: the frontend could not reach or parse the backend response.

## Answer Tabs

When an answer comes back, the UI shows:

- `Answer`: the written answer, with clickable citation numbers;
- `Sources`: source cards built from backend citations;
- `Trace`: locators, relevance labels, namespaces, and readiness labels when present.

This is useful for internal review because it keeps answer text and source trace close together.

## Useful Commands

Install dependencies:

```bash
npm install
```

Run development server:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Build:

```bash
npm run build
```

Lint:

```bash
npm run lint
```

Preview a built app:

```bash
npm run preview
```

## Common Problems

If the UI says the backend is not connected, check that the backend is running on port `8000`.

If upload fails, check that the backend is running and that the file type is supported.

If the browser cannot open `127.0.0.1:5173`, check that the Vite terminal and the SSH tunnel terminal are both still open.
