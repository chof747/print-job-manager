# ADR-0005: Parse Known Embedded G-code Metadata

- Status: Accepted
- Date: 2026-07-27

## Context

Modern slicers often embed useful planning data in G-code comments or metadata blocks. Treating the file as opaque would require repetitive manual entry; fully interpreting toolpaths would add disproportionate complexity.

## Decision Drivers

- minimize manual input
- improve scheduling and inventory data quality
- retain a focused scope
- support multiple slicers incrementally

## Considered Options

1. Never parse G-code.
2. Parse known metadata formats.
3. Build a full G-code interpreter and toolpath analyzer.

## Decision

The application parses known embedded metadata and normalizes supported values, including where available:

- estimated print duration
- filament weight or length
- material
- nozzle diameter
- layer height
- object dimensions
- thumbnail
- slicer and version
- printer profile information

The original G-code remains unchanged. The application does not fully interpret or simulate toolpaths.

## Rationale

Known metadata supplies high-value planning information without turning the product into a slicer or simulation engine.

## Consequences

### Positive

- faster job creation
- richer scheduling and UI data
- extractor support can grow format by format

### Negative and Risks

- metadata formats vary by slicer and version
- parser errors or stale source metadata may produce incorrect values

## Follow-up

- define extractor interface and parser provenance
- create a supported-slicer test corpus
- specify malformed and unsupported metadata behavior
