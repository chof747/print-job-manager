# ADR-0004: One Uploaded G-code File Defines a Print Job

- Status: Accepted
- Date: 2026-07-27

## Context

The project could manage source models, slicer projects, generated artifacts, or ready-to-print files. Supporting the full design and slicing workflow would significantly expand scope and couple the system to slicer-specific concepts.

## Decision Drivers

- keep the product focused on print management and execution
- make execution deterministic
- remain slicer-agnostic
- avoid owning CAD and slicing workflows

## Considered Options

1. Upload G-code directly with the job.
2. Reference an externally stored G-code file.
3. Reference a model or slicer project and generate G-code later.
4. Manage multiple source and generated artifacts per job.

## Decision

Every print job is defined by one uploaded G-code file. The G-code is the canonical execution artifact.

The system does not generate, edit, optimize, or regenerate G-code and does not manage CAD models or slicer projects as part of the job definition.

## Rationale

Using ready-to-print G-code creates a clear system boundary and allows users to continue using any slicer they choose.

## Consequences

### Positive

- narrow, understandable scope
- deterministic execution artifact
- limited slicer coupling

### Negative and Risks

- changing print settings requires uploading a different G-code file
- source-model history and reslicing remain outside the system

## Follow-up

- define storage, checksum, size limits, and supported upload formats
- define duplication or replacement flow when execution data must change
