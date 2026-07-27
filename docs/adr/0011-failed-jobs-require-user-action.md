# ADR-0011: Failed Jobs Require Explicit User Action

- Status: Accepted
- Date: 2026-07-27

## Context

After a failed print, the system could automatically reschedule the job, apply failure-specific recovery policies, or wait for a user decision. Failure causes are often physical and cannot be inferred safely from software signals alone.

## Decision Drivers

- avoid wasting time and material through unsafe retries
- keep recovery decisions with the user
- separate scheduling from operational diagnosis

## Considered Options

1. Automatically return every failed job to scheduling.
2. Leave failed jobs waiting for explicit user action.
3. Configure an automatic policy per failure type.

## Decision

A failed job remains in the failed state and does not automatically re-enter scheduling.

The user must explicitly choose the next action, such as retrying, duplicating, cancelling, or otherwise resolving the job.

## Rationale

The execution system can report that a print failed, but it cannot reliably determine whether the printer, material, environment, or G-code is safe for another attempt.

## Consequences

### Positive

- prevents uncontrolled repeat failures
- preserves clear responsibility for recovery
- keeps scheduler responsibilities narrow

### Negative and Risks

- failed jobs can remain unresolved
- users need a clear failure inbox and recovery workflow

## Follow-up

- define available recovery actions and their lifecycle effects
- define printer maintenance or blocking behavior after relevant failures
- capture failure evidence useful for the user’s decision
