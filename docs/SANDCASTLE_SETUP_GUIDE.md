# Sandcastle Setup Guide For Generic Repos

This guide captures the working Sandcastle setup learned from the `AFK Ralph TDD agent workflow setup` session. Use it when adding Sandcastle to a new repository so the sandbox can read issues, implement work in an isolated worktree, run repo checks, push a branch, create a PR, and update issue labels without manual rescue steps.

## 1. Install Sandcastle In The Repo

Install Sandcastle and the runner dependencies in the repo root:

```sh
npm install --save-dev @ai-hero/sandcastle tsx typescript
```

Add root scripts to `package.json`:

```json
{
  "scripts": {
    "sandcastle": "tsx --env-file=.sandcastle/.env .sandcastle/main.mts",
    "sandcastle:docker:build": "docker build -f .sandcastle/Dockerfile -t sandcastle:<repo-name> .",
    "sandcastle:docker": "SANDCASTLE_SANDBOX=docker tsx --env-file=.sandcastle/.env .sandcastle/main.mts",
    "sandcastle:dry-run": "SANDCASTLE_DRY_RUN=true tsx --env-file=.sandcastle/.env .sandcastle/main.mts"
  }
}
```

Replace `<repo-name>` with a stable local image name.

## 2. Create Sandcastle Runtime Files

Create `.sandcastle/` with at least:

```text
.sandcastle/
  .env.example
  Dockerfile
  main.mts
  prompt-template.md or repo-specific agent instructions
```

Ignore runtime state in `.gitignore`:

```gitignore
.sandcastle/.env
.sandcastle/logs/
.sandcastle/worktrees/
```

Keep instruction files committed. Keep tokens, logs, and generated worktrees untracked.

## 3. Configure Environment Variables

Create `.sandcastle/.env` from `.sandcastle/.env.example`.

Minimum `.env.example`:

```sh
OPENCODE_API_KEY=
GH_TOKEN=
SANDCASTLE_REPO=<owner>/<repo>
SANDCASTLE_READY_LABEL=ready-for-agent
SANDCASTLE_IDLE_TIMEOUT_SECONDS=1800
SANDCASTLE_MAX_ITERATIONS=5
SANDCASTLE_LOG_VERBOSE=false
SANDCASTLE_INSTALL_PROJECT_DEPS=true
SANDCASTLE_INSTALL_NODE_DEPS=true
SANDCASTLE_EXISTING_WORKTREE_PATH=
```

Required GitHub token permissions:

- Classic PAT: `repo` scope.
- Fine-grained PAT: repository access for the target repo, `Contents: Read and write`, `Pull requests: Read and write`, `Issues: Read and write`, `Metadata: Read-only`.

The important lesson from the session: a token that can read issues is not enough. Sandcastle finalization also needs `git push`, `gh pr create`, `gh pr comment`, and `gh issue edit`.

Verify the token from `.sandcastle/.env`:

```sh
GH_TOKEN=$(grep '^GH_TOKEN=' .sandcastle/.env | cut -d= -f2-) gh auth status
```

If diagnosing push auth, run commands as one line so shell line continuations do not get mangled:

```sh
GH_TOKEN=$(grep '^GH_TOKEN=' .sandcastle/.env | cut -d= -f2-) GIT_CONFIG_GLOBAL=/tmp/sandcastle-gh-gitconfig gh auth setup-git
```

Then from a Sandcastle worktree or test branch:

```sh
GH_TOKEN=$(grep '^GH_TOKEN=' /absolute/path/to/repo/.sandcastle/.env | cut -d= -f2-) GIT_CONFIG_GLOBAL=/tmp/sandcastle-gh-gitconfig git push --dry-run -u origin HEAD
```

## 4. Build A Sandbox Image With Base Tooling

The Docker image owns base tooling. Agents must not install OS packages, bootstrap `pip`, install Node, or download installer scripts during implementation.

Use a Dockerfile like this for Node plus Python repos:

```dockerfile
FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
  ca-certificates \
  git \
  curl \
  gpg \
  jq \
  python3 \
  python3-pip \
  python3-venv \
  make \
  g++ \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p -m 755 /etc/apt/keyrings \
  && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
  && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && apt-get update \
  && apt-get install -y gh \
  && rm -rf /var/lib/apt/lists/*

ARG AGENT_UID=1000
ARG AGENT_GID=1000

RUN groupmod -o -g $AGENT_GID node \
  && usermod -o -u $AGENT_UID -g $AGENT_GID -d /home/agent -m -l agent node

RUN npm install -g opencode-ai@latest

USER ${AGENT_UID}:${AGENT_GID}
WORKDIR /home/agent
ENTRYPOINT ["sleep", "infinity"]
```

Build after any Dockerfile change:

```sh
npm run sandcastle:docker:build
```

Also ensure Docker Desktop has enough memory. Around 4 GB was the practical minimum for Sandcastle plus OpenCode in this repo.

## 5. Put GitHub Auth Inside The Sandbox

The runner should pass `GH_TOKEN` and `GITHUB_TOKEN` into the sandbox and run `gh auth setup-git` before the agent starts.

Recommended Docker sandbox environment:

```ts
env: {
  HOME: "/home/agent",
  GH_TOKEN: process.env.GH_TOKEN ?? process.env.GITHUB_TOKEN ?? "",
  GITHUB_TOKEN: process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN ?? "",
  PATH: "/home/agent/workspace/node_modules/.bin:/tmp/sandcastle-python/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
  XDG_STATE_HOME: "/tmp/opencode-state",
  XDG_CACHE_HOME: "/tmp/opencode-cache"
}
```

Recommended first sandbox hook:

```sh
mkdir -p /tmp/opencode-state /tmp/opencode-cache /home/agent/.local/share/opencode/log && cp /home/agent/host-auth/auth.json /home/agent/.local/share/opencode/auth.json && gh auth setup-git
```

Mount host OpenCode auth/config read-only if the local setup needs it:

```ts
mounts: [
  {
    hostPath: "~/.local/share/opencode/auth.json",
    sandboxPath: "/home/agent/host-auth/auth.json",
    readonly: true
  },
  {
    hostPath: "~/.config/opencode",
    sandboxPath: "/home/agent/.config/opencode",
    readonly: true
  }
]
```

## 6. Install Declared Project Dependencies Before The Agent Starts

The main failure mode in the session was confusing base tooling with project dependencies.

Base tooling belongs in the Docker image:

- `node`, `npm`, `python3`, `pip`, `venv`, `gh`, `git`, compilers.

Project dependencies belong in runner-owned sandbox setup hooks:

- Node dependencies from `package-lock.json` or `package.json`.
- Python dependencies from committed requirements files.
- Other ecosystems from their lockfiles or declared dependency manifests.

Do not ask the agent to bootstrap these during implementation. The agent should stop and report an environment blocker if tooling is missing.

Recommended Python hook for a Python/FastAPI repo:

```sh
python3 -m venv /tmp/sandcastle-python && . /tmp/sandcastle-python/bin/activate && if [ -f backend/requirements.txt ]; then python -m pip install -r backend/requirements.txt; fi && if [ -f backend/tests/requirements.txt ]; then python -m pip install -r backend/tests/requirements.txt; fi && python -m pytest --version
```

If the repo expects specific imports, add an import smoke check, for example:

```sh
python -c 'import fastapi, uvicorn'
```

Recommended Node hook:

```sh
if [ -f package.json ]; then if [ -f package-lock.json ]; then npm ci; else npm install; fi; fi && if [ -f package.json ]; then npm exec vitest -- --version; fi
```

The PATH must include both dependency bin directories before the agent runs:

- `/home/agent/workspace/node_modules/.bin`
- `/tmp/sandcastle-python/bin`

Without this PATH fix, installed tools like `vitest` or `pytest` may still be invisible to later agent commands.

## 7. Add A Tooling Smoke Hook

Add an early hook that proves the sandbox can run the base tools before installing repo dependencies:

```sh
python3 -m pip --version && python3 -m venv /tmp/sandcastle-venv-check && rm -rf /tmp/sandcastle-venv-check && node --version && npm --version && gh --version
```

This catches missing `python3-venv`, `pip`, `npm`, or `gh` before an agent wastes iterations diagnosing the environment.

## 8. Generate Issue And Resume Prompts Deliberately

For a new issue run, the runner should:

- Read a specific `SANDCASTLE_ISSUE_NUMBER`, or select the oldest open issue with `SANDCASTLE_READY_LABEL`.
- Include issue title, URL, body, labels, and comments in the prompt.
- Instruct the agent to read repo-specific Sandcastle role files and project docs.
- Define the completion gate as full PR finalization, not merely passing tests.

Completion should require:

- Final QA checklist gathered.
- Review findings handled.
- Changes committed.
- Branch pushed with `git push -u origin HEAD`.
- PR created with `gh pr create`.
- PR body includes `Closes #<issue-number>`.
- Handover comment posted with `gh pr comment`.
- Issue labels updated with `gh issue edit`.
- Only then output `<promise>COMPLETE</promise>`.

For resumed runs, pass both the issue number and worktree path:

```sh
SANDCASTLE_ISSUE_NUMBER=37 \
SANDCASTLE_MAX_ITERATIONS=10 \
SANDCASTLE_EXISTING_WORKTREE_PATH=.sandcastle/worktrees/feat-issue-37-bootstrap-split-app-shell \
npm run sandcastle:docker
```

Resume mode resumes the filesystem state, not model memory. The resume prompt must tell the agent to inspect `git status`, recent commits, existing files/tests, and PR state before continuing.

If you set `SANDCASTLE_PROMPT`, remember it replaces the generated issue/resume prompt. Include all essentials yourself.

## 9. Use Safe Branch And Worktree Behavior

Recommended branch naming:

- `enhancement` issue label -> `feat/issue-<number>-<short-slug>`.
- `bug` issue label -> `bug/issue-<number>-<short-slug>`.
- neither -> `issue/issue-<number>-<short-slug>`.

Recommended branch strategy:

- New run: create/use a Sandcastle branch for the issue.
- Resume run with `SANDCASTLE_EXISTING_WORKTREE_PATH`: use `branchStrategy: { type: "head" }` and `cwd: existingWorktreePath`.
- Custom prompt without issue selection: use a strategy that matches your intended current-head workflow.

Do not expect resume mode to delete the worktree. In resume mode Sandcastle works in a user-specified existing directory, so automatic removal would be unsafe.

If a run fails, preserve the worktree and resume it. If a PR is created but the worktree remains, inspect it:

```sh
git status --short --branch
git worktree list
```

Only remove it when clean or when you have intentionally handled uncommitted changes:

```sh
git worktree remove .sandcastle/worktrees/<branch-name>
```

Force removal only when you intentionally want to discard uncommitted changes:

```sh
git worktree remove --force .sandcastle/worktrees/<branch-name>
```

## 10. Validate Before The First Real Run

Run these checks before giving Sandcastle real work:

```sh
npm run sandcastle:docker:build
```

```sh
SANDCASTLE_DRY_RUN=true SANDCASTLE_ISSUE_NUMBER=<number> npm run sandcastle:dry-run
```

```sh
GH_TOKEN=$(grep '^GH_TOKEN=' .sandcastle/.env | cut -d= -f2-) gh auth status
```

If possible, test push auth from a temporary branch or preserved worktree:

```sh
GH_TOKEN=$(grep '^GH_TOKEN=' /absolute/path/to/repo/.sandcastle/.env | cut -d= -f2-) GIT_CONFIG_GLOBAL=/tmp/sandcastle-gh-gitconfig git push --dry-run -u origin HEAD
```

Then run a bounded first issue:

```sh
SANDCASTLE_ISSUE_NUMBER=<number> SANDCASTLE_MAX_ITERATIONS=3 npm run sandcastle:docker
```

## First-Time Setup Checklist

- Sandcastle package and `tsx` are installed.
- `package.json` has `sandcastle`, `sandcastle:docker:build`, `sandcastle:docker`, and `sandcastle:dry-run` scripts.
- `.sandcastle/.env` is ignored and `.sandcastle/.env.example` is committed.
- `GH_TOKEN` can read issues, push contents, create PRs, comment on PRs, and edit issue labels.
- Docker image contains base tooling: `git`, `gh`, `node`, `npm`, `python3`, `pip`, `venv`, and native build tools if needed.
- Docker image has been rebuilt after Dockerfile changes.
- Sandbox startup runs `gh auth setup-git`.
- Sandbox startup verifies base tools.
- Sandbox startup installs project dependencies from committed manifests, not ad-hoc agent commands.
- PATH includes project dependency bins, especially `node_modules/.bin` and Python venv `bin`.
- Prompt completion gate requires full PR and issue finalization before `<promise>COMPLETE</promise>`.
- Resume mode has explicit instructions and uses the preserved worktree path.
- Worktree cleanup expectations are documented: dirty or resumed worktrees are preserved.
