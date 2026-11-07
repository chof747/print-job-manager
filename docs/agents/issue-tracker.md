# Issue tracker: GitHub

Issues and PRDs live in GitHub Issues at `chof747/print-job-manager`.
Use the `gh` CLI to list, read, create, comment on, label, and close issues.

## Conventions

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`; also fetch labels.
- List: `gh issue list --state open`, with appropriate label filters.
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: `gh issue close <number> --comment "..."`

Use a heredoc for multiline bodies. The repository is inferred from the remote.

## Pull requests as a triage surface

**PRs as a request surface: no.**

When a skill says to publish to the issue tracker, create a GitHub issue.
When it asks to fetch a ticket, read the issue and its comments.
