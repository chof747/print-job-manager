# ADR-0009: The Scheduler Selects the Next Job

- Status: Accepted
- Date: 2026-07-27

## Context

A multi-printer system could derive execution order from a global queue, maintain independent printer queues, or let a scheduler select from a global pool of active jobs.

## Decision Drivers

- support multiple printers without duplicated queues
- allow scheduling strategies to evolve
- centralize and test assignment decisions
- preserve the distinction between eligibility and ranking

## Considered Options

1. Select the first compatible job from a global ordered queue.
2. Let each printer maintain and consume its own queue.
3. Let a scheduler evaluate all active jobs and select the best eligible candidate.

## Decision

The scheduler is the sole authority for selecting which job should run next on an available printer.

It evaluates the global pool of active jobs, applies hard constraints and manual directives, ranks eligible candidates, and creates an assignment.

The queue is a projection of active jobs and current scheduling order, not the source of truth for selection.

## Rationale

Centralized scheduling allows the algorithm to evolve from simple priority-based ordering to more sophisticated optimization without changing printer or job ownership.

## Consequences

### Positive

- strategy-based scheduling is possible
- no per-printer queue duplication
- assignment logic remains centralized and explainable

### Negative and Risks

- the scheduler becomes a critical component
- concurrency, stale printer state, and duplicate assignments require careful control

## Follow-up

- define the default scheduling strategy
- define assignment idempotency and concurrency handling
- provide human-readable explanations for selections
