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

## Sandcastle AFK Builds

Sandcastle can pick up GitHub issues and implement them in an isolated worktree using the ralph-loop instructions in `.sandcastle/`.

GitHub writes use the `gh` CLI inside the sandbox. Make sure `.sandcastle/.env` contains a `GH_TOKEN` with repository write access; the sandbox runs `gh auth setup-git` so `git push` can authenticate.

Normal Sandcastle logs are human-readable. Set `SANDCASTLE_LOG_VERBOSE=true` only when debugging provider stream issues; it prints raw OpenCode JSON events and is intentionally noisy.

The sandbox installs project-declared backend dependencies into a temporary venv before the agent starts, so agents can verify backend code without bootstrapping tooling themselves. Set `SANDCASTLE_INSTALL_PROJECT_DEPS=false` to skip this setup.

The sandbox also installs Node dependencies before the agent starts, so frontend tools like Vitest are available on `PATH`. Set `SANDCASTLE_INSTALL_NODE_DEPS=false` to skip this setup.

Build the local Sandcastle Docker image after changing `.sandcastle/Dockerfile`:

```sh
npm run sandcastle:docker:build
```

### Start A New Build

Run the next open issue labeled `ready-for-agent`:

```sh
npm run sandcastle:docker
```

Run a specific issue:

```sh
SANDCASTLE_ISSUE_NUMBER=37 npm run sandcastle:docker
```

By default, the runner allows up to `5` agent iterations and stops earlier when the orchestrator outputs `<promise>COMPLETE</promise>`. In this repo, `COMPLETE` means the PR flow is done: QA checklist gathered, final review handled, changes committed and pushed, PR created, handover comment posted, and issue labels updated.

Override the iteration limit for larger issues:

```sh
SANDCASTLE_ISSUE_NUMBER=37 SANDCASTLE_MAX_ITERATIONS=10 npm run sandcastle:docker
```

Preview the generated prompt without starting the agent:

```sh
SANDCASTLE_DRY_RUN=true SANDCASTLE_ISSUE_NUMBER=37 npm run sandcastle:dry-run
```

Sandcastle creates a branch based on issue labels:

- `enhancement` -> `feat/issue-<number>-<short-slug>`
- `bug` -> `bug/issue-<number>-<short-slug>`
- neither -> `issue/issue-<number>-<short-slug>`

### Resume An Interrupted Build

If Sandcastle fails, it preserves the dirty worktree and prints a path like:

```text
Worktree preserved at .sandcastle/worktrees/feat-issue-37-bootstrap-split-app-shell
```

Resume against that preserved worktree:

```sh
SANDCASTLE_ISSUE_NUMBER=37 \
SANDCASTLE_MAX_ITERATIONS=10 \
SANDCASTLE_EXISTING_WORKTREE_PATH=.sandcastle/worktrees/feat-issue-37-bootstrap-split-app-shell \
npm run sandcastle:docker
```

This resumes the worktree state, not the previous model session memory. The orchestrator will inspect the current files and continue from the next unfinished behavior.

Do not remove the preserved worktree before resuming. After the PR is created successfully, Sandcastle should clean up its own worktree.
