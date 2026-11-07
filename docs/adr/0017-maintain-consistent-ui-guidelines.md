# ADR-0017: Maintain Consistent UI Guidelines

- Status: Accepted
- Date: 2026-11-08

## Context

Inconsistent controls and save interactions make the application harder to use
and lead to repeated UI corrections. The project needs a shared standard that
can grow as interface patterns are agreed without requiring a new architectural
decision for every visual or interaction detail.

## Decision Drivers

- make common interactions and input controls predictable across screens
- make the standard discoverable when implementing and reviewing UI changes
- allow detailed patterns to evolve without rewriting architectural history

## Considered Options

1. Let each screen establish its own UI patterns.
2. Record every UI rule and styling detail in an ADR.
3. Establish a durable commitment to consistency and maintain the detailed
   rules in a living guidelines document.

## Decision

The application will follow a consistent, documented UI standard. The living
[UI guidelines](../UI_GUIDELINES.md) are the source for current interaction
rules and visual implementation details. Frontend changes should follow those
guidelines, and agreed patterns should be added to them as they evolve.

This decision does not require every existing screen to be immediately compliant;
the guidelines describe the intended standard rather than guaranteeing current
implementation behavior.

## Rationale

A shared standard reduces inconsistent behavior and presentation, while a living
document makes ordinary refinements easier to maintain than a sequence of ADRs.
The ADR records the commitment and its rationale; the guidelines describe how to
apply it.

## Consequences

### Positive

- UI work and reviews have a discoverable common reference
- detailed visual and interaction rules can evolve together

### Negative and Risks

- existing screens can diverge from the standard until they are updated
- the guidelines require maintenance and review to remain useful and consistent

## Follow-up

- apply the guidelines when implementing or reviewing frontend changes
- update existing screens to conform as appropriate and extend the guidelines
  when new patterns are agreed
