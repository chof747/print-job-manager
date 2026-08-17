# Handover Instructions

Generate the final PR handover using the `/handoff` skill.

The handover is posted as a PR comment after the PR exists. Do not commit it as a repo file by default.

## Include

- issue context
- implemented behaviors
- test strategy and commands reported by the tester
- review findings fixed
- remaining HILT findings, if any
- QA checklist summary or pointer to the PR body section
- branch and worktree details
- what another agent should do if manual QA finds problems

If HILT findings exist, make clear that the user is expected to reply to the `HILT findings` PR comment and rerun Sandcastle pointing at that comment.
