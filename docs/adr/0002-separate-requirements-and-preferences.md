# ADR-0002: Separate Requirements and Preferences

- Status: Accepted
- Date: 2026-07-27

## Context

Scheduling must distinguish conditions that make execution invalid from factors that merely make one valid assignment better than another.

## Decision Drivers

- keep compatibility rules explainable
- prevent optimization from violating execution constraints
- allow scheduling strategies to evolve independently

## Considered Options

1. Represent every job attribute as an equal scheduling input.
2. Separate hard requirements from soft preferences.

## Decision

A print job distinguishes:

- **Requirements:** constraints that must be satisfied for eligibility.
- **Preferences:** inputs used to rank eligible candidates.

Scheduling occurs in two conceptual stages:

1. filter ineligible printer-job combinations
2. rank the remaining candidates

## Rationale

The separation answers two different questions: whether a job can run on a printer and whether it should run there next.

## Consequences

### Positive

- invalid assignments cannot be selected by optimization
- eligibility and ranking can be tested independently
- new preferences do not alter compatibility semantics

### Negative and Risks

- each new field must be deliberately classified
- contradictory rules require explicit validation and diagnostics

## Follow-up

- define the initial requirement and preference catalog
- expose eligibility failures in user-facing explanations
