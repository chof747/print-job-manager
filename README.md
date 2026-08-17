# print-job-manager
A managing app that allows planning of 3d printing jobs based on projects and a prioritised list of models

## App shell

This repo now includes a minimal split MVP shell:

- `backend/` contains the FastAPI app entrypoint and health/config endpoints.
- `frontend/` contains the React/Vite TypeScript shell.
- `frontend/public/runtime-config.json` provides the runtime API base URL used before React renders.

## Root commands

- `npm run dev:backend` starts the FastAPI app with Uvicorn.
- `npm run dev:frontend` starts the Vite frontend from the repo root with the frontend Vite config.
- `npm run check:frontend` runs the frontend Vitest suite.
- `python3 -m pytest backend/tests -q` or `npm run check:backend` runs the backend tests when Python test dependencies are installed.
