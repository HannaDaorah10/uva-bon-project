# Frontend Overview

The frontend is the part of the project that people see in the browser.

Right now there is one frontend app:

```text
frontend/bon-ui/
```

It is a React app built with Vite and TypeScript.

## What The Frontend Does

The frontend:

- shows the NatureDesk assistant page;
- lets a user type a question;
- lets a user choose a local model;
- lets a user upload a temporary file;
- sends questions to the backend;
- shows answers, refusals, source cards, and trace details.

The frontend does not decide whether evidence is safe. That decision belongs to the backend.

## Main Files

```text
frontend/
`-- bon-ui/
    |-- src/App.tsx        # Main UI logic
    |-- src/App.css        # Main UI styling
    |-- src/main.tsx       # React entry point
    |-- vite.config.ts     # Vite config and backend proxy
    |-- package.json       # npm scripts and dependencies
    `-- public/            # Static icons and public files
```

## Development Commands

Start the UI on Spark:

```bash
cd ~/naturedesk/uva-bon-project/frontend/bon-ui
npm run dev -- --host 127.0.0.1 --port 5173
```

Build the UI:

```bash
cd frontend/bon-ui
npm run build
```

Lint the UI:

```bash
cd frontend/bon-ui
npm run lint
```

## Backend Proxy

In development, the UI calls backend routes like `/api/query` and `/api/upload`.

Vite forwards those calls to the backend server. By default it forwards to:

```text
http://127.0.0.1:8000
```

You can point the UI to another backend with:

```bash
NATUREDESK_BACKEND_URL=http://127.0.0.1:8000 npm run dev
```

## More Detail

Read [bon-ui/README.md](bon-ui/README.md) for the detailed UI app guide.
