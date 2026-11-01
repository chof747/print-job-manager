# Project instructions

## Pull requests and database migrations

In every pull request description, explicitly state whether a database migration
is required. When one is required, include the command `pnpm run migrate:backend`
and any relevant migration or deployment considerations.

## Temporary pre-launch data policy

While this project is in development and has not gone live, preserving existing
application data across schema changes or migrations is not required. Development
data may be treated as disposable when designing changes.

This is a temporary rule. Before the application goes live, the owner will revoke
it and establish the appropriate data-preservation requirements. It does not
authorize deleting unrelated files or user work, or performing destructive
operations without the required confirmation.
