# print-job-manager
A managing app that allows planning of 3d printing jobs based on projects and a prioritised list of models

## Sandcastle AFK Builds

Sandcastle can pick up GitHub issues and implement them in an isolated worktree using the ralph-loop instructions in `.sandcastle/`.

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
