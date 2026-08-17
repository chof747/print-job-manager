# Architecture Decision Records

This directory contains accepted architectural decisions for Print Job Manager.

ADRs capture decisions that materially shape the system and would be costly or confusing to reverse without an explicit record. Fine implementation details should remain in specifications, tickets, or code unless they establish a durable architectural constraint.

## Status Values

- **Proposed** — under active discussion
- **Accepted** — current project decision
- **Superseded** — replaced by a later ADR
- **Deprecated** — retained for history but no longer recommended

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-printer-assignment-semantics.md) | Printer assignment supports unassigned, preferred, and required modes | Accepted |
| [0002](0002-separate-requirements-and-preferences.md) | Hard requirements are distinct from soft preferences | Accepted |
| [0003](0003-jobs-reference-material-attributes.md) | Jobs reference material attributes, not specific spools | Accepted |
| [0004](0004-gcode-defines-a-print-job.md) | A print job is defined by one uploaded G-code file | Accepted |
| [0005](0005-parse-embedded-gcode-metadata.md) | Known embedded G-code metadata is parsed | Accepted |
| [0006](0006-extracted-metadata-is-authoritative.md) | Extracted metadata is authoritative when present | Accepted |
| [0007](0007-require-complete-job-data.md) | All required planning data must exist before job creation | Accepted |
| [0008](0008-retain-job-history.md) | Jobs remain in the system through terminal lifecycle states | Accepted |
| [0009](0009-scheduler-selects-the-next-job.md) | The scheduler is the authority for job selection | Accepted |
| [0010](0010-support-manual-scheduling-overrides.md) | Users may provide explicit scheduling overrides | Accepted |
| [0011](0011-failed-jobs-require-user-action.md) | Failed jobs do not retry automatically | Accepted |
| [0012](0012-immutable-execution-mutable-scheduling.md) | Execution data is immutable after queueing; scheduling data remains mutable | Accepted |
| [0013](0013-use-numeric-job-priority.md) | Job priority is numeric | Accepted |
| [0014](0014-check-inventory-at-assignment-time.md) | Inventory is checked during eligibility and reserved when an assignment is created | Accepted |
| [0015](0015-separate-fastapi-app-assembly-from-route-modules.md) | FastAPI app assembly is separate from route modules | Accepted |

## Creating a New ADR

Use this structure:

```markdown
# ADR-NNNN: Decision title

- Status: Proposed
- Date: YYYY-MM-DD

## Context

What problem or architectural tension requires a durable decision?

## Decision Drivers

- Driver one
- Driver two

## Considered Options

1. Option A
2. Option B

## Decision

State the chosen option precisely.

## Rationale

Explain why this option best satisfies the drivers.

## Consequences

### Positive

### Negative and Risks

## Follow-up

List specification, implementation, or documentation work implied by the decision.
```

When a decision changes, prefer creating a new ADR that supersedes the old one rather than rewriting history.
