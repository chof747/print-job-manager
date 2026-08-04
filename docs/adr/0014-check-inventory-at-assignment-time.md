# ADR-0014: Check Inventory at Assignment Time and Reserve on Assignment

- Status: Accepted
- Date: 2026-08-04

## Context

Jobs reference material attributes rather than specific physical spools. The remaining open question is when inventory state should affect job flow: only as an informational signal, as a hard eligibility gate, or as an earlier reservation before the scheduler commits a job to a printer.

The decision must fit the existing architecture in which:

- jobs own material requirements but not spool identity
- eligibility and ranking are separate stages
- the scheduler is the authority that creates assignments
- assignments may later be released, cancelled, or become stale before execution starts

## Decision Drivers

- keep job definitions stable while inventory changes
- prevent double-booking the same material resource
- align inventory behavior with the scheduler's existing assignment boundary
- preserve clear explanations for why a job is or is not runnable
- avoid reserving scarce material too early and blocking the queue unnecessarily

## Considered Options

1. Treat inventory as advisory only and never reserve material.
2. Check inventory only at execution handoff and reserve then.
3. Check inventory as part of eligibility and reserve a concrete material resource when an assignment is created.
4. Reserve inventory earlier, such as when a job is created or enters the ready queue.

## Decision

Inventory availability is part of job eligibility for the MVP.

The scheduler must check whether suitable material inventory is currently available before it creates an assignment.

When the scheduler creates an assignment, the system reserves a concrete inventory resource for that assignment. The reservation is released if the assignment is cancelled, becomes stale, or is otherwise cleared before print start.

The system does not reserve material when a job is created, uploaded, or merely waiting in the ready pool.

Actual depletion remains an execution and inventory reconciliation concern after print completion or failure; it does not mutate the job's material requirement definition.

## Rationale

This keeps the decision boundary aligned with the scheduler pipeline already established by the architecture: eligibility first, then assignment. Inventory shortage is a hard constraint, so it belongs in eligibility rather than only affecting ranking or execution-time surprise handling.

Reserving at assignment time is the earliest point where the system has actually committed to a specific printer-job execution decision. Reserving earlier would couple queue presence to scarce inventory and create unnecessary blocking when many ready jobs compete for the same material. Reserving later would allow multiple assignments to appear valid against the same stock and push preventable conflicts into execution.

## Consequences

### Positive

- jobs remain independent of spool identity until the system commits to execution
- inventory shortage can be explained as a clear eligibility failure or derived blocked condition
- assignment becomes the single place where double-booking prevention starts
- released or stale assignments can return material capacity cleanly by dropping the reservation

### Negative and Risks

- assignment persistence now needs explicit reservation lifecycle rules
- stale inventory state can still produce temporary misassignments if integrations lag
- execution may consume more or less than estimated, requiring later reconciliation
- the system needs a deterministic reservation policy when multiple matching resources exist

## Follow-up

- define assignment persistence, idempotency, and cancellation rules together with reservation release behavior
- define the reservation-selection policy when multiple matching inventory resources are available
- define how eligibility explanations expose material shortage versus printer incompatibility
- define reconciliation rules between estimated usage, reserved material, and actual post-print consumption
