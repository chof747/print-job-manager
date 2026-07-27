# ADR-0012: Execution Data Is Immutable After Queueing

- Status: Accepted
- Date: 2026-07-27

## Context

Users may need to change scheduling details after a job enters the queue, but changing the artifact or technical requirements in place would make historical and active records ambiguous.

## Decision Drivers

- preserve a trustworthy record of what will be or was printed
- allow operational priorities to change
- prevent silent mutation of execution intent

## Considered Options

1. Make the entire queued job immutable.
2. Allow all job fields to remain editable.
3. Make execution data immutable while allowing scheduling data to change.

## Decision

Once a job is queued:

- **Execution data is immutable**, including the G-code file, extracted metadata, material and printer requirements, estimated duration and material usage, and artifact checksum.
- **Scheduling data remains mutable**, including numeric priority, due date, notes, tags, and manual scheduling directives.

Changing execution data requires creating a new job, normally by duplicating the existing job and preserving lineage.

## Rationale

The decision protects execution and audit integrity while allowing day-to-day planning to adapt.

## Consequences

### Positive

- completed records remain trustworthy
- scheduling remains flexible
- replacement jobs have explicit identities and histories

### Negative and Risks

- apparently small corrections may require duplication
- lineage and cancellation behavior must be clear to users

## Follow-up

- define the exact queued boundary
- define duplication and lineage fields
- classify every editable field as execution or scheduling data
