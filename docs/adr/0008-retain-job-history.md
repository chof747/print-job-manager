# ADR-0008: Retain Jobs Through Terminal Lifecycle States

- Status: Accepted
- Date: 2026-07-27

## Context

Completed jobs could be removed from the active queue and discarded, moved into a separate history model, or retained as the same durable job records with terminal states.

## Decision Drivers

- preserve auditability and traceability
- support reporting and operational analytics
- avoid duplicating job data between queue and history models

## Considered Options

1. Retain jobs and expose active queue and history as filtered views.
2. Remove completed jobs from the queue and copy them into a separate history store.
3. Delete completed jobs after execution.

## Decision

Jobs remain in the system throughout their lifecycle, including terminal states such as completed, failed, and cancelled.

The active queue and job history are projections or filtered views of the same job repository.

## Rationale

A durable job record provides a consistent foundation for audit, statistics, material reporting, printer reliability analysis, and future optimization.

## Consequences

### Positive

- complete lifecycle history
- one job identity across active and historical views
- simpler reporting relationships

### Negative and Risks

- storage and retention policies must be defined
- sensitive or large artifacts may require archival or deletion rules

## Follow-up

- define retention, archival, and permitted deletion behavior
- define lifecycle event history and reporting fields
