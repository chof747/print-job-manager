# ADR-0001: Printer Assignment Semantics

- Status: Accepted
- Date: 2026-07-27

## Context

Some jobs may run on any compatible printer, while others should favor or require a particular printer. Treating every selected printer as a hard assignment would unnecessarily restrict scheduling; treating it only as a hint would make printer-specific jobs unsafe.

## Decision Drivers

- preserve scheduler flexibility
- support printer-specific operational constraints
- express user intent unambiguously
- avoid redesign when multiple printers are introduced

## Considered Options

1. Every selected printer is a hard assignment.
2. Every selected printer is only a preference.
3. Support unassigned, preferred, and required modes.

## Decision

A job supports three printer assignment modes:

- **Unassigned:** any compatible printer may execute the job.
- **Preferred:** the scheduler should favor the selected printer but may choose another compatible printer.
- **Required:** only the selected printer may execute the job.

## Rationale

The three modes separate user intent from scheduler freedom and allow both automatic optimization and strict printer-specific execution.

## Consequences

### Positive

- flexible multi-printer scheduling
- explicit representation of hard and soft printer choices
- no need for per-printer queues

### Negative and Risks

- UI and API must clearly distinguish preferred from required
- scheduling explanations must show when a preference was overridden

## Follow-up

- define validation when the selected printer becomes unavailable or incompatible
- define how assignment mode appears in the job-creation UI
