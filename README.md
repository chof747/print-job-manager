# print-job-manager
A managing app that allows planning of 3d printing jobs based on projects and a prioritised list of models

## Production images

The publishing workflow builds separate `linux/amd64` images in GHCR:

- `ghcr.io/<owner>/print-job-manager-backend:<commit-sha>`
- `ghcr.io/<owner>/print-job-manager-frontend:<commit-sha>`

Replace `<owner>` with the lowercase GitHub repository owner and `<commit-sha>`
with the triggering commit SHA. Images published from `main` also receive the
`latest` tag. The deployment configuration belongs in the separate install repository.

### Deployment and publication recovery

For a consistent deployment, use the paired backend and frontend digest references
from the **Publish container images** workflow's successful run. In GitHub Actions,
open that run and download its `image-digests-<commit-sha>` artifact; the
`image-digests.txt` file contains `backend` and `frontend` references to use together
in the install repository. Do not independently resolve mutable tags for a pair.
The artifact is uploaded after both SHA pushes succeed, but a subsequent `latest`
promotion can still fail, so check the overall workflow result.

Both images are built once and checked before publication. SHA tags are mutable:
a retry rebuilds and rechecks both images, republishes both SHA tags, and records
the resulting digest pair, which may differ from the previous run. Neither SHA
pushes nor `latest` promotion are atomic. A failure or interruption can leave a
partial or inconsistent tag pair; rerun the workflow for the commit to rebuild,
recheck and republish both images, then use the new artifact. For `latest` recovery,
run the workflow for current `main`; it promotes the recorded pair.

The workflow checks that `main` has not advanced before promoting `latest`, but
`main` can advance after that check and promotion is still not atomic. A newer
successful main run should repair `latest`. Restrict GHCR package write access to
trusted publishers: workflow concurrency does not prevent other authorized writers
from changing tags.

The frontend image uses copies of the root `package.json`, `pnpm-lock.yaml`, and
`pnpm-workspace.yaml` in `frontend/` because it has a separate build context.
After updating any of these root files, copy all three into `frontend/`, commit
the copies with the originals, and run `pnpm run check:frontend-image-deps`.
Image publication runs this check before building.

### Image runtime configuration

- The backend listens on container port `8000` and runs as UID/GID `65532`.
  Set `PRINT_JOB_MANAGER_DATABASE_URL` to the reachable PostgreSQL database URL
  (using `postgresql+psycopg://`). Set `PRINT_JOB_MANAGER_FRONTEND_ORIGIN` to
  the browser's frontend origin when it differs from the default.
- Set `PRINT_JOB_MANAGER_ARTIFACT_STORAGE_PATH` to a persistent mounted directory
  writable by UID/GID `65532`. The default is `data/artifacts` relative to
  `/app/backend`; the image does not provision a writable persistent directory.
- The frontend listens on container port `8080` and runs as UID/GID `101`.
  To configure its API endpoint without rebuilding, mount a JSON file at
  `/usr/share/nginx/html/runtime-config.json` that is readable by UID/GID `101`, for example
  `{"apiBaseUrl":"/api/v1"}`. The URL must be reachable from the browser.
  For a relative URL, configure an external reverse proxy to route `/api/v1`
  to the backend; the frontend image itself does not proxy API requests.

The backend automatically runs `alembic upgrade head` before starting; migration
failure prevents startup. Ensure PostgreSQL is ready and the database user can
apply migrations. Coordinate deployments so migrations do not run concurrently.
Check schema compatibility with both old and new application versions before a
rolling deployment. Before rollout, plan backups and a rollback: switching back
to an older image does not reverse migrations, and an older image may not support
the upgraded schema. Assess the relevant Alembic downgrade and data-loss risks
before any schema rollback; the pre-launch policy below does not guarantee data
preservation.

## Backend Setup

The backend uses `uv` with `backend/pyproject.toml` and `backend/uv.lock`.

Sync backend runtime and test dependencies from a clean checkout:

```sh
uv sync --project backend --group test
```

Run the backend test suite from the repo root:

```sh
pnpm run check:backend
```

The full suite requires a running PostgreSQL server and a **disposable**, separate
test database. By default, its URL comes from `PRINT_JOB_MANAGER_DATABASE_URL`,
with `_test` appended to the database name. Create that database first, or set
`PRINT_JOB_MANAGER_TEST_DATABASE_URL` in `backend/.env` (see `backend/.env.example`)
or in the environment to choose a different disposable database.
The database user must be able to create and drop schemas. The command runs the
PostgreSQL tests rather than silently skipping them; it does not create the database.
Tests migrate and downgrade their schemas, so never use a database with valuable data.

### Pre-launch migration rollback

During pre-launch development, database data is disposable and schema downgrades
do not guarantee data preservation. In particular, downgrading past the job
scheduling migrations can discard scheduling fields and reset scheduling versions.
After a rollback and re-upgrade, discard cached edits and reload job details before
editing; old versions cannot reliably detect stale writes. Revisit this policy
before production. Never use this policy as permission to delete unrelated data.

### Disposable database for manual PR testing

With `PRINT_JOB_MANAGER_DATABASE_URL` in `backend/.env` pointing to the original
database, stop the backend and disconnect other clients from it, then run:

```sh
pnpm run db:clone 61
```

Replace `61` with the PR number. This creates `<original>_pr_61` from the original database, including its data,
schemas and object permissions, and copies database ownership and grants. PostgreSQL
roles are cluster-wide and are reused. The connecting role needs permission to
clone the source, assign the owner, and reproduce its grants. Existing clones are
never overwritten. If grant copying fails, the incomplete clone is left for inspection.
If the application role lacks these privileges, set `PRINT_JOB_MANAGER_ADMIN_DATABASE_URL`
in `backend/.env` to a privileged connection on the same server; the application URL
still determines which database to clone. The admin connection is also used to dispose
of the clone.

Copy the artifact-storage directory separately, then configure the PR backend to
use the clone and copied storage before running migrations. When finished, stop
clients connected to the clone, restore the **original** database URL in
`backend/.env`, and run `pnpm run db:dispose 61` with the same PR number. Type the clone name when prompted;
this permanently deletes the clone, not its separately copied artifact files.

Start the FastAPI backend dev server from the repo root:

```sh
pnpm run dev:backend
```

## Sandcastle AFK Builds

Sandcastle can pick up GitHub issues and implement them in an isolated worktree using the ralph-loop instructions in `.sandcastle/`.

GitHub writes use the `gh` CLI inside the sandbox. Make sure `.sandcastle/.env` contains a `GH_TOKEN` with repository write access; the sandbox runs `gh auth setup-git` so `git push` can authenticate.

Normal Sandcastle logs are human-readable. Set `SANDCASTLE_LOG_VERBOSE=true` only when debugging provider stream issues; it prints raw OpenCode JSON events and is intentionally noisy.

Docker runs mount the host's `~/.agents/skills` directory read-only so OpenCode can discover the skills required by the Ralph loop. Ensure `tdd`, `code-review`, and `handoff` are installed there before starting a run. The `handoff` skill may be hidden from the automatic skill list; the orchestrator loads it explicitly by ID.

The sandbox resolves project-declared backend dependencies through `uv` before the agent starts, so agents can verify backend code without bootstrapping tooling themselves. Set `SANDCASTLE_INSTALL_PROJECT_DEPS=false` to skip this setup.

The sandbox also installs Node dependencies with pnpm before the agent starts, so frontend tools like Vitest are available on `PATH`. Set `SANDCASTLE_INSTALL_NODE_DEPS=false` to skip this setup.

This repository is pnpm-managed: `pnpm-lock.yaml` is the sole Node lockfile, `package.json` pins the pnpm release, and `pnpm-workspace.yaml` declares permitted dependency build scripts. Agents normally run root check commands rather than invoking a package manager directly. They may add an issue-required, named project dependency with `pnpm` when they commit the manifest and lockfile together and document why. Python dependency additions use `uv add` or `uv lock`, with `backend/pyproject.toml` and `backend/uv.lock` committed together.

Build the local Sandcastle Docker image after changing `.sandcastle/Dockerfile`:

```sh
pnpm run sandcastle:docker:build
```

The Dockerfile pins the OpenCode CLI version (`@opencode/cli`). When upgrading OpenCode to a new major version or another breaking release, update that pin to the compatible version before rebuilding the image. Do not use the legacy `opencode-ai` package: it installs OpenCode 1.x and is incompatible with the V2 OAuth credentials used by Sandcastle.

Docker runs export the host's OpenAI account with `opencode auth export openai` and import it into the sandbox using OpenCode V2's credential commands. Connect OpenAI on the host first (`opencode auth login openai`). The temporary export contains secrets and is removed when the run exits normally; if the process is forcibly terminated, remove any leftover `sandcastle-auth-*` directory from the system temporary directory securely.

### Start A New Build

Run the next open issue labeled `ready-for-agent`:

```sh
pnpm run sandcastle:docker
```

Run a specific issue:

```sh
SANDCASTLE_ISSUE_NUMBER=37 pnpm run sandcastle:docker
```

By default, the runner allows up to `5` agent iterations and stops earlier when the orchestrator outputs `<promise>COMPLETE</promise>`. In this repo, `COMPLETE` means the PR flow is done: QA checklist gathered, final review handled, changes committed and pushed, PR created, handover comment posted, and issue labels updated.

Override the iteration limit for larger issues:

```sh
SANDCASTLE_ISSUE_NUMBER=37 SANDCASTLE_MAX_ITERATIONS=10 pnpm run sandcastle:docker
```

Preview the generated prompt without starting the agent:

```sh
SANDCASTLE_DRY_RUN=true SANDCASTLE_ISSUE_NUMBER=37 pnpm run sandcastle:dry-run
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
pnpm run sandcastle:docker
```

This resumes the worktree state, not the previous model session memory. The orchestrator will inspect the current files and continue from the next unfinished behavior.

Do not remove the preserved worktree before resuming. Resume mode uses an existing user-specified worktree, so it is preserved by default. Remove it manually only after it is clean and you are done with it.
