# ADR-0003: Jobs Reference Material Attributes, Not Specific Spools

- Status: Accepted
- Date: 2026-07-27

## Context

A print job needs material information for compatibility and planning. Binding the job to one physical spool would couple job definition to mutable inventory state.

## Decision Drivers

- keep jobs stable when inventory changes
- allow suitable material resources to be selected later
- avoid respecifying a job when a spool is replaced, moved, or exhausted

## Considered Options

1. Reference one specific spool from the job.
2. Reference only required material attributes.
3. Store material attributes plus an optional preferred or reserved spool.

## Decision

A print job references material requirements only, such as material type, color, diameter, and estimated consumption. It does not reference a specific spool.

## Rationale

The job describes what material is needed; inventory describes which resources are currently available. The scheduler or execution workflow matches those concerns without making inventory identity part of the job definition.

## Consequences

### Positive

- inventory changes do not mutate jobs
- matching remains flexible
- the model supports replacement and replenishment naturally

### Negative and Risks

- deterministic spool selection requires a separate inventory policy
- actual material consumption and depletion must be reconciled outside the job definition

## Follow-up

- define when inventory availability is checked
- define whether and when material is allocated or reserved
