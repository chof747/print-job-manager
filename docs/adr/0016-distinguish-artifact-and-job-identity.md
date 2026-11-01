# ADR-0016: Distinguish Artifact and Print-Job Identity

- Status: Accepted
- Date: 2026-10-28

## Context

The same uploaded G-code can be printed multiple times. Content identity alone cannot distinguish those requests or their independent lifecycle and scheduling data.

## Decision Drivers

- reuse identical stored G-code without conflating print requests
- retain independent job state and history

## Considered Options

1. Use the artifact identity as the job identity and allow only one job per artifact.
2. Identify artifacts by content and assign each print job its own identity.

## Decision

An artifact is identified by the SHA-256 digest of its G-code content. Each job has a separate generated identity and references one artifact. Multiple jobs may reference the same artifact, with independent execution snapshots, scheduling data, lifecycle state, and history.

This complements [ADR-0004](0004-gcode-defines-a-print-job.md): each job still has one canonical G-code artifact.

## Rationale

Content-based artifact identity allows reuse while separate job identities represent distinct requests to print the same content.

## Consequences

### Positive

- repeated print requests retain separate identities and history
- identical content can be stored and referenced as one artifact

### Negative and Risks

- artifact references must not be treated as unique job identifiers
- shared artifact retention must account for all referencing jobs

## Follow-up

- define artifact retention and deletion policy separately from job lifecycle
