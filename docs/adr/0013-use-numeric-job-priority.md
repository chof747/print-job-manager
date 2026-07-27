# ADR-0013: Use Numeric Job Priority

- Status: Accepted
- Date: 2026-07-27

## Context

The scheduler needs an explicit representation of relative job importance. Fixed labels are easy to understand but limit automation and fine ordering; relying only on due dates would omit urgency that is independent of time.

## Decision Drivers

- support fine-grained relative importance
- integrate cleanly with automation and external inputs
- avoid a fixed set of semantic labels in the domain model

## Considered Options

1. Use an integer priority.
2. Use fixed levels such as low, normal, high, and urgent.
3. Do not store explicit priority.
4. Use fixed levels plus numeric ordering within each level.

## Decision

Each job has a numeric integer priority. Zero is the default; higher values represent greater relative importance. Negative values may represent background or lower-priority work.

The scheduler consumes the numeric value directly. A UI may map configurable ranges to friendly labels, but those labels are not part of the core domain model.

## Rationale

An integer is simple, automation-friendly, and avoids hard-coding organization-specific priority vocabulary.

## Consequences

### Positive

- precise ordering signal
- straightforward API and automation integration
- no migration needed to add more priority levels

### Negative and Risks

- users may assign arbitrary or inflated values
- the meaning of differences between values is not yet defined
- interaction with due dates and manual directives requires specification

## Follow-up

- define validation bounds, if any
- define how priority contributes to the default scheduling strategy
- define UI controls and guidance that discourage priority inflation
