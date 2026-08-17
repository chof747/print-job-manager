# ADR-0015: Separate FastAPI App Assembly from Route Modules

- Status: Accepted
- Date: 2026-08-17

## Context

The split app shell starts with only a few backend endpoints, but future implementation slices will add many more API routes. If all route handlers live directly in `backend/app/main.py`, the application entrypoint will become a mixed composition, configuration, and feature implementation module.

The backend needs a stable convention before product endpoints are added so new slices have an obvious place to put route code.

## Decision Drivers

- keep the FastAPI app entrypoint small and predictable
- make route ownership visible from the filesystem layout
- avoid route sprawl in `main.py` as API surface grows
- preserve a clear boundary between operational root endpoints and versioned application API endpoints

## Considered Options

1. Keep all endpoints directly in `backend/app/main.py` until the file becomes painful.
2. Split only versioned API routes, but keep root operational endpoints in `main.py`.
3. Keep `main.py` as app assembly only and put route handlers in focused router modules.

## Decision

`backend/app/main.py` is responsible for FastAPI app assembly only: creating the app, configuring middleware, and including routers.

Root operational endpoints live in focused modules such as `backend/app/health.py`.

Versioned application API endpoints live under `backend/app/api/v1/`. The `/api/v1` root route belongs in `backend/app/api/v1/root.py`; `/api/v1` health belongs in `backend/app/api/v1/health.py`; future `/api/v1` endpoints should be added to focused modules under the same version directory rather than directly to `main.py`.

## Rationale

This makes the early shell structure match the intended growth path. New feature slices can add route modules without changing the app entrypoint beyond router inclusion, and readers can distinguish process-level health endpoints from application API endpoints by path and package structure.

Waiting until `main.py` becomes crowded would create unnecessary churn later and invite inconsistent placement during early implementation.

## Consequences

### Positive

- `main.py` remains a shallow composition module
- endpoint ownership is easier to navigate
- API versioning has a concrete filesystem home from the first application routes
- future route modules can be tested and reviewed independently

### Negative and Risks

- the initial shell has more files than a single-file FastAPI app
- router aggregation needs care so prefixes are applied exactly once

## Follow-up

- apply this placement rule to future backend slices that add `/api/v1` endpoints
- revisit the package structure when a second API version or larger domain package emerges
