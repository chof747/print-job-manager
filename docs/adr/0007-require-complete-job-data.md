# ADR-0007: Require Complete Planning Data Before Job Creation

- Status: Accepted
- Date: 2026-07-27

## Context

The system could allow incomplete drafts, proceed with unknown planning values, or require all essential information before a job enters the system.

## Decision Drivers

- guarantee schedulable, valid jobs
- keep lifecycle and domain rules simple
- avoid hidden uncertainty during compatibility checks

## Considered Options

1. Block creation until all required values are known.
2. Allow incomplete drafts but block scheduling or execution.
3. Allow jobs with unknown values to proceed.

## Decision

A print job is created only after all required planning values are available.

The import flow extracts available metadata, identifies missing required values, asks the user only for those values, and creates the job after validation succeeds.

## Rationale

The application can provide a low-friction import flow without introducing an incomplete-job state into the core job lifecycle.

## Consequences

### Positive

- every created job is valid for eligibility evaluation
- no separate draft lifecycle is required
- missing data is resolved close to import

### Negative and Risks

- an upload cannot be saved as a job when the user cannot supply a required value
- temporary upload state may still be needed while the creation interaction is in progress

## Follow-up

- define the required-field catalog
- define cleanup of abandoned uploads
- provide clear validation and missing-field messages
