# Backend Overview

The backend contains the server and workflow code behind the NatureDesk prototype.

There are three important backend areas:

```text
backend/
|-- server/        # Active FastAPI assistant backend
|-- inputRouting/  # Standalone BON workflow wrappers
`-- synthesis/     # Older synthesis prototype material
```

## The Active Assistant Backend

The active backend is:

```text
backend/server/
```

This is the server used by the web UI.

It provides:

- `GET /health`
- `POST /api/upload`
- `POST /api/query`

The assistant route is guarded. It checks safety, routing, evidence readiness, handlers, and citations before returning an answer.

Read [server/README.md](server/README.md) for details.

## Standalone BON Workflow Wrappers

The workflow wrapper code is:

```text
backend/inputRouting/
```

These scripts can prepare inputs for BON in a Box, start BON runs, and collect outputs.

They are not the normal chat assistant route.

Read [inputRouting/README.md](inputRouting/README.md) before running them.

## Older Synthesis Prototype

The older synthesis prototype is:

```text
backend/synthesis/
```

This is useful background for prompt and response experiments, but it is not the current FastAPI server entry point.

Read [synthesis/README.md](synthesis/README.md) for details.

## Normal Assistant Flow

```text
frontend question
  -> FastAPI /api/query
  -> preflight safety gate
  -> route classifier
  -> evidence gate
  -> route handler
  -> citation validator
  -> answer or refusal
```

## Keep These Separate

Do not quietly connect the standalone BON workflow scripts to `/api/query`.

The chat route should answer or refuse from controlled evidence. The workflow scripts can start actions and write output files. That requires a different safety design.
