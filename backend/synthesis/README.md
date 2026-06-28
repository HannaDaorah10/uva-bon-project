# Older Synthesis Prototype

This folder contains older prompt and synthesis experiments.

It is useful background, but it is not the active FastAPI assistant server.

The active backend entry point is:

```text
backend/server/main.py
```

## What Is Here

```text
backend/synthesis/
|-- synthesis_prompt.md
|-- qwen_synthesis.py
|-- bon_synthesis.py
|-- dummy_chunks.py
|-- validate_synthesis.py
|-- validate_response.py
|-- validate_refusal.py
|-- *_answer.md
|-- test_*.md
`-- requirements.txt
```

## How To Treat This Folder

Use this folder for:

- understanding earlier synthesis ideas;
- testing prompt shapes;
- reviewing example answer and refusal formats.

Do not assume this folder controls the current web assistant.

Current assistant answers are produced through the guarded backend in `backend/server/`, especially `main.py`, `handlers/`, and `synthesis.py`.

## Safety Note

Do not copy older prototype behavior into the live assistant if it bypasses current gates. The active backend must keep preflight checks, evidence gates, route handlers, and citation validation.
