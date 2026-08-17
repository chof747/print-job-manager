# Technology Stack

This document records the accepted MVP technology stack for Print Job Manager. Agents must consult it before choosing frameworks, libraries, test tools, package managers, or runtime commands.

Source decision: GitHub issue #31, `Wayfinder Ticket: MVP Technology Stack`.

## Application Shape

- Split backend/frontend web application.
- Backend: Python/FastAPI.
- Frontend: React/Vite/TypeScript.
- Boundary: explicit REST/OpenAPI API under `/api/v1`.
- Database: PostgreSQL database named `print_job_manager`.
- Packaging: separate backend and frontend containers.

## Backend

- Python 3.13.
- FastAPI served by Uvicorn directly.
- `uv` for dependency management with `pyproject.toml` and `uv.lock`.
- PostgreSQL through psycopg 3.
- SQLAlchemy 2.0 synchronous ORM.
- Alembic migrations.
- Pydantic Settings for environment-driven configuration.
- Domain/use-case-oriented modules.
- Separate API schemas, persistence models, and domain objects at real boundaries.
- Thin repository protocols with SQLAlchemy implementations.
- FastAPI dependencies at the API edge; explicit wiring internally.
- Custom exact-key G-code metadata parser; no third-party G-code parser dependency initially.

## Frontend

- React + Vite + TypeScript.
- pnpm for Node tooling.
- TanStack Router.
- TanStack Query.
- OpenAPI-generated TypeScript API client from FastAPI.
- Feature-specific query/mutation hooks wrap the generated client.
- React Hook Form for non-trivial forms.
- Runtime `/config.json` loaded and Zod-validated before React renders.
- No Storybook initially.
- English-only MVP; no i18n framework initially.
- No dedicated hotkey library initially.

## Testing And Quality

- Backend tests: pytest under `backend/tests/`.
- Backend migration tests: pytest against disposable PostgreSQL.
- Frontend unit/component tests: Vitest and React Testing Library under `frontend/tests/`.
- Frontend critical-flow tests: Playwright under `frontend/e2e/`.
- Backend quality: Ruff and mypy.
- Frontend quality: TypeScript check, ESLint, and Prettier.
- Active pre-commit should include formatting, linting, fast pytest, fast Vitest, and frontend typecheck.
- Playwright is CI/manual only unless an issue explicitly requires critical-flow coverage.

## Local Development

- Root pnpm convenience scripts for development, tests, checks, and Sandcastle.
- Backend dev server: `localhost:8000`.
- Frontend Vite dev server: `localhost:3000`.
- Local development uses configured external/shared PostgreSQL unless a test Compose setup is explicitly introduced.

## Packaging And Deployment

- Backend image uses Python 3.13 slim and `uv.lock`.
- Frontend image uses Node 22, `pnpm-lock.yaml`, and unprivileged Nginx where practical.
- Separate Docker contexts: `./backend` and `./frontend`.
- Production deployment uses a separate install repository.
- App repo owns local/dev Compose only.

## Agent Rules

- Do not introduce a different framework, runtime, package manager, or test runner without an explicit issue requirement or human decision.
- Backend behavior tests must not be written with Node's `node:test`; use pytest.
- Frontend tests must not replace Vitest/React Testing Library or Playwright with another test stack without human approval.
- Prefer no new dependency. If a dependency is necessary, justify why the accepted stack does not already cover the need.
