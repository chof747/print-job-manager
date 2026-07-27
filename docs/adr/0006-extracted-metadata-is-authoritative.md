# ADR-0006: Extracted Metadata Is Authoritative

- Status: Accepted
- Date: 2026-07-27

## Context

When a value exists both in the uploaded G-code metadata and as potential user input, the system needs a deterministic source of truth.

## Decision Drivers

- avoid conflicting job definitions
- minimize unnecessary questions
- preserve deterministic interpretation of the uploaded artifact

## Considered Options

1. Parsed metadata always wins.
2. User-entered values always win.
3. Store both and allow a user-confirmed override.

## Decision

When a supported value is present in extracted G-code metadata, that value is authoritative. The user is asked only for required information that is absent from the metadata.

Normal job creation does not provide a user override for extracted values.

## Rationale

The G-code is the canonical execution artifact. Treating its metadata as authoritative keeps job creation predictable and prevents silent divergence between the artifact and the planning record.

## Consequences

### Positive

- fewer user decisions
- deterministic import behavior
- clear source of truth

### Negative and Risks

- incorrect source metadata or parser output cannot be corrected through ordinary field editing
- parser diagnostics and provenance become important

## Follow-up

- define a repair workflow for parser defects or incorrect source metadata
- retain extraction provenance where useful
