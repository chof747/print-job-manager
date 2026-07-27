# ADR-0010: Support Explicit Manual Scheduling Overrides

- Status: Accepted
- Date: 2026-07-27

## Context

Automatic scheduling cannot know every real-world urgency or operational exception. Fully manual ordering, however, would discard the benefits of intelligent scheduling.

## Decision Drivers

- automate ordinary scheduling
- preserve deliberate human control for exceptions
- keep overrides visible and explainable

## Considered Options

1. Never allow users to override scheduling.
2. Make queue ordering completely manual.
3. Let the scheduler optimize while respecting explicit user directives.

## Decision

Users may apply explicit manual scheduling directives. The scheduler must respect those directives as constraints while optimizing all remaining jobs.

Candidate directive types include pinning a job, placing it after another job, freezing its position, and returning it to scheduler control. Their exact semantics remain to be specified.

## Rationale

This combines automation by default with intentional human intervention when the scheduler lacks important contextual knowledge.

## Consequences

### Positive

- urgent or exceptional work can be accommodated
- most jobs remain automatically optimized
- user intervention is explicit rather than hidden in arbitrary data edits

### Negative and Risks

- conflicting or impossible directives must be detected
- excessive overrides may reduce scheduling quality

## Follow-up

- define the initial directive set and precedence rules
- define conflict resolution and user feedback
- show why a job position is scheduler-derived or manually constrained
