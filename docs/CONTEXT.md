# Print Job Manager — Project Context

This document captures the shared language, boundaries, and architectural principles of Print Job Manager. It is a living document: accepted decisions are recorded in `docs/adr/`, while unresolved questions remain here until they are decided.

## Vision

Print Job Manager coordinates uploaded, ready-to-print G-code across one or more compatible printers. It automates metadata extraction, validates that every job is complete, selects the best eligible job for an available printer, and delegates execution to the printer integration.

The system should automate decisions it can make confidently and require explicit user input where operational or business judgment is needed.

## Scope

The system owns:

- G-code upload and storage
- extraction of known G-code metadata
- validation of required planning data
- print-job lifecycle and history
- printer capability and availability information
- eligibility matching between jobs and printers
- scheduling and manual scheduling directives
- execution handoff and status tracking
- material requirements used for planning

## Non-goals

The system does not:

- create, edit, optimize, or regenerate G-code
- manage CAD models or slicer projects
- interpret full toolpaths or simulate prints
- automatically retry failed prints
- bind a job permanently to a physical filament spool

## Guiding Principles

1. **G-code is the execution source of truth.** A print job is created around one uploaded G-code file.
2. **Metadata first.** Extract known values automatically and ask only for required values that are missing.
3. **Complete jobs only.** A job is not created until all required planning information is known.
4. **Hard constraints and soft preferences are separate.** Eligibility answers whether a job can run; scheduling answers whether it should run next.
5. **The scheduler owns job selection.** Printers and queue views do not independently select the next job.
6. **Users may deliberately override scheduling.** Manual directives are respected as constraints while the scheduler optimizes the remaining jobs.
7. **Execution data is immutable after queueing.** Scheduling data may remain editable.
8. **Failures require human judgment.** Failed jobs remain failed until the user explicitly chooses an action.
9. **History is retained.** Completed, failed, and cancelled jobs remain available for audit and reporting.
10. **One authority per decision.** Each domain decision has a clear owner.

## Ubiquitous Language

### Print Job

A validated request to execute one uploaded G-code file. A job contains immutable execution data, mutable scheduling data, and a lifecycle state.

### G-code File

The canonical artifact executed by a printer. The application may read embedded metadata but does not modify or fully interpret the file.

### Extracted Metadata

Values read from known G-code comments or metadata blocks, such as estimated duration, filament usage, material, nozzle diameter, dimensions, thumbnail, slicer, or printer profile. Extracted values are authoritative when present.

### Missing Required Value

A planning value required to create a valid job but absent from extracted metadata. The user must provide it before job creation is completed.

### Requirement

A hard constraint that must be satisfied before a printer is eligible to execute a job.

Examples include material, minimum build volume, nozzle constraints, enclosure, hardened nozzle, multi-material capability, or a required printer.

### Preference

A soft input used to rank otherwise eligible scheduling candidates. A preference may be outweighed by other optimization goals.

### Printer Assignment Mode

The relationship between a job and a selected printer:

- **Unassigned:** any compatible printer may execute the job.
- **Preferred:** the scheduler should favor the selected printer but may choose another compatible printer.
- **Required:** only the selected printer may execute the job.

### Eligibility

The result of evaluating all hard requirements against printer capabilities and current operational constraints.

Question answered: **Can this job run on this printer?**

### Scheduling

Ranking eligible jobs and selecting the best candidate for an available printer.

Question answered: **Which eligible job should run next?**

### Scheduler

The component that evaluates the global pool of active jobs, filters eligible candidates, applies manual directives, and selects assignments according to the active scheduling strategy.

### Queue

A user-facing projection of active jobs and the scheduler’s current ordering. The queue is not the authority for selecting the next job.

### Manual Scheduling Directive

An explicit user instruction that constrains scheduling, such as pinning a job, placing it after another job, freezing its position, or returning it to scheduler control.

### Execution Data

Data that determines what is printed. Once queued, it is immutable.

Examples: G-code file, extracted metadata, material requirements, estimated duration and usage, printer requirements, and file checksum.

### Scheduling Data

Data that affects when a job is printed and may be changed after queueing.

Examples: numeric priority, due date, notes, tags, and manual scheduling directives.

### Numeric Priority

An integer expressing relative importance. Higher values represent higher importance; zero is the default. The exact interaction with other scheduling objectives remains to be specified.

### Failed Job

A job whose execution did not complete successfully. It does not re-enter scheduling automatically and awaits explicit user action.

## Domain Boundaries

### Jobs

Owns job identity, immutable execution definition, mutable scheduling data, lifecycle, and historical record.

### Printers

Owns printer identity, capabilities, availability, and operational status.

### Scheduling

Owns eligibility evaluation, candidate ranking, scheduling strategies, assignments, and manual directives.

### Execution

Owns transfer or handoff to the printer integration and translates printer events into controlled lifecycle transitions.

### Inventory

Owns available material resources. Jobs declare material attributes rather than referencing a specific spool.

These boundaries are provisional and will be refined as later epics are grilled.

## Core Workflow

```text
Upload G-code
      |
      v
Store original file
      |
      v
Detect format or slicer and extract known metadata
      |
      v
Identify missing required planning values
      |
      v
Ask the user only for missing values
      |
      v
Create a complete print job
      |
      v
Add it to the global active-job pool
      |
      v
Evaluate eligibility and scheduling directives
      |
      v
Select assignment when a printer is available
      |
      v
Execute and record lifecycle outcome
```

## Authority Map

| Decision | Authority |
|---|---|
| What will be executed | Uploaded G-code and extracted metadata |
| Missing required information | User |
| Printer capabilities and state | Printer domain/integration |
| Job eligibility | Eligibility rules |
| Which job runs next | Scheduler |
| Manual exception to scheduling | User |
| Execution outcome | Execution integration |
| Retry after failure | User |

## Job Model

A job is conceptually divided into three parts:

```text
Print Job
  |-- Execution Data   (immutable after queueing)
  |-- Scheduling Data  (mutable)
  `-- Lifecycle State  (controlled transitions)
```

A change to immutable execution data creates a new job, normally by duplicating the existing job and preserving lineage.

## Lifecycle

Exact state names and transitions remain to be specified. The accepted direction is that jobs remain in the system through terminal states such as completed, failed, and cancelled.

A failed job remains failed until the user explicitly retries, duplicates, cancels, or otherwise resolves it.

## Decision Records

See [`docs/adr/README.md`](adr/README.md) for the decision index.

## Open Questions

The following details were intentionally deferred:

- exact required fields for job creation
- precise lifecycle states and transition rules
- numeric-priority range, validation, and weighting
- due-date semantics and interaction with priority
- exact set and semantics of manual scheduling directives
- scheduling strategy interface and default algorithm
- compatibility rule representation
- retention and deletion policy, including whether users may delete historical jobs
- parser support matrix and behavior for malformed or contradictory metadata
- execution handoff, idempotency, and printer-offline behavior
- definition of material compatibility

These questions should be resolved one at a time during epic refinement and recorded here or in a new ADR when the decision is significant and hard to reverse.
