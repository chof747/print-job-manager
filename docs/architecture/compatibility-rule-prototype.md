# Compatibility Rule Prototype

This is a rough wayfinding artifact for "Wayfinder Ticket: Compatibility Rule Representation".

## Current MVP Decision

The MVP should use a fixed typed requirement catalog, not a generic rule DSL.

- material type is an exact requirement
- material color and amount are inventory concerns, not printer-capability rules
- nozzle diameter is an exact requirement
- hardened nozzle is a boolean requirement
- build volume is checked per axis using `required <= available`
- enclosure is a boolean requirement
- printer-specific constraints reuse `unassigned`, `preferred`, and `required`

## Proposed Shape

Model eligibility as a fixed typed catalog of requirement fields, not a generic rule DSL.

- `job.requirements.material`
- `job.requirements.nozzle`
- `job.requirements.build_volume`
- `job.requirements.environment`
- `job.requirements.printer`

- `printer.capabilities.material`
- `printer.capabilities.nozzle`
- `printer.capabilities.build_volume`
- `printer.capabilities.environment`
- `printer.id`
- `inventory.resources[*]`
- `printer.operational_state`

Each requirement field maps to one evaluator with a stable failure code. Eligibility is the conjunction of all evaluators.

Some evaluators compare against pure printer capabilities. Others compare against facts owned by adjacent domains that still participate in eligibility, such as inventory availability or the printer's current operational state.

## Sketch

```yaml
job:
  requirements:
    material:
      type: PETG
      color: black
      diameter_mm: 1.75
      amount_g: 120
    nozzle:
      diameter_mm: 0.4
      hardened_required: true
    build_volume:
      x_mm: 180
      y_mm: 180
      z_mm: 120
    environment:
      enclosure_required: true
    printer:
      assignment_mode: required
      printer_id: voron-2.4

printer:
  id: voron-2.4
  capabilities:
    material:
      supported_types: [PLA, PETG, ABS, ASA]
      supported_diameter_mm: [1.75]
    nozzle:
      diameter_mm: 0.4
      hardened: true
    build_volume:
      x_mm: 350
      y_mm: 350
      z_mm: 330
    environment:
      enclosed: true

  operational_state:
    accepting_jobs: true
    loaded_material:
      type: PETG
      color: black
      diameter_mm: 1.75

inventory:
  resources:
    - spool_id: spool-123
      material:
        type: PETG
        color: black
        diameter_mm: 1.75
      available_g: 850
      status: available
```

## Evaluation Layers

Eligibility is still one yes-or-no answer, but not every hard check comes from the printer capability record.

### Printer capability checks

These answer whether the printer is technically able to run the job at all.

- material type support
- filament diameter support
- nozzle diameter
- hardened nozzle presence
- build volume
- enclosure
- required printer id

### Alongside checks

These are still hard eligibility checks, but they compare the job against adjacent domain facts rather than static printer capabilities.

- inventory match: is there at least one available material resource with matching type, color, and diameter?
- inventory sufficiency: does at least one matching resource have enough material for the required amount?
- printer acceptance state: is the printer currently accepting jobs, or is it paused for maintenance, faulted, or otherwise unavailable for assignment?
- optionally, loaded-material policy: if the MVP later decides to prefer or require currently loaded material for some printers, that would be a separate operational or ranking concern, not a rewrite of the capability model

The important boundary is:

- printer capabilities describe what the printer can do in general
- alongside checks describe whether this specific job can be assigned now given current inventory and operational facts

## Checker Module Layout

The MVP can keep one overall eligibility pipeline while splitting the hard checks into three checker types:

- `PrinterCapabilityEligibilityChecker`
- `InventoryEligibilityChecker`
- `PrinterOperationalEligibilityChecker`

Each checker receives the same evaluation context and returns either pass or structured failure reasons.

```ts
type EligibilityContext = {
  job: Job;
  printer: Printer;
  inventorySnapshot: InventorySnapshot;
  printerOperationalState: PrinterOperationalState;
};

type EligibilityFailure = {
  code: string;
  requirement: string;
  detail?: unknown;
};

type EligibilityResult = {
  eligible: boolean;
  failures: EligibilityFailure[];
};
```

The scheduler-facing orchestrator runs all three checker types, collects failures, and marks the printer-job pair eligible only when every hard checker passes.

### PrinterCapabilityEligibilityChecker

Owns static technical fit:

- material type support
- filament diameter support
- nozzle diameter
- hardened nozzle
- build volume
- enclosure
- required printer id

### InventoryEligibilityChecker

Owns current material availability:

- at least one matching material resource exists
- at least one matching resource has enough material

### PrinterOperationalEligibilityChecker

Owns current printer assignability:

- printer is accepting jobs
- printer is not in a state that blocks assignment, such as maintenance or fault, if those are modeled as hard gates

## Evaluation Rules

- material type: printer must support the requested material type
- material color: not printer compatibility; this is inventory compatibility
- material diameter: printer must advertise support for the requested filament diameter; inventory must also later match that diameter
- material amount: not printer compatibility; this is inventory availability
- nozzle diameter: printer nozzle must exactly match the required diameter
- hardened nozzle: printer must have a hardened nozzle when required
- build volume: each required axis must be less than or equal to the printer axis
- enclosure: printer must be enclosed when required
- printer accepting jobs: printer operational state must allow new assignments
- printer assignment mode:
  - `unassigned`: no printer-specific eligibility rule
  - `preferred`: not an eligibility rule; used only for ranking
  - `required`: printer id must match exactly

Hard requirements fail closed. If a required capability is missing or unknown on the printer, the printer is ineligible until that capability is recorded explicitly.

The same fail-closed rule applies to alongside checks. If a required inventory or operational fact is missing or unknown, the system should not treat the job as eligible.

## Why This Shape

- keeps accepted requirement vs preference separation explicit
- makes eligibility explanations deterministic and easy to test
- avoids inventing a mini-language before the requirement catalog is stable
- leaves room to add new capability types by extending the catalog one field at a time

## Example Result

```json
{
  "eligible": false,
  "failures": [
    {
      "code": "enclosure_required",
      "requirement": "job.requirements.environment.enclosure_required",
      "printer_value": false
    },
    {
      "code": "required_printer_mismatch",
      "requirement": "job.requirements.printer.printer_id",
      "printer_value": "mk4-01"
    }
  ]
}
```

## Alongside Check Examples

### Example 1: Printer-capable but inventory-blocked

The printer supports PETG, 1.75 mm filament, 0.4 mm nozzle, hardened nozzle, build volume, and enclosure requirements.

The job is still ineligible if no available spool matches `PETG + black + 1.75 mm` with enough remaining material.

```json
{
  "eligible": false,
  "failures": [
    {
      "code": "inventory_material_unavailable",
      "requirement": "job.requirements.material",
      "needed": {
        "type": "PETG",
        "color": "black",
        "diameter_mm": 1.75,
        "amount_g": 120
      }
    }
  ]
}
```

This failure would come from `InventoryEligibilityChecker`, while `PrinterCapabilityEligibilityChecker` would still pass.

### Example 2: Inventory OK but printer not accepting jobs

The printer is technically compatible, and a matching spool exists, but the printer is faulted or in maintenance.

```json
{
  "eligible": false,
  "failures": [
    {
      "code": "printer_not_accepting_jobs",
      "requirement": "printer.operational_state.accepting_jobs",
      "printer_value": false
    }
  ]
}
```

This failure would come from `PrinterOperationalEligibilityChecker`, while the printer capability and inventory checkers would pass.

### Example 3: Missing fact fails closed

The job requires `1.75 mm`, but the printer record has no supported filament diameters recorded yet.

```json
{
  "eligible": false,
  "failures": [
    {
      "code": "unknown_printer_filament_diameter_support",
      "requirement": "printer.capabilities.material.supported_diameter_mm"
    }
  ]
}
```

This failure would come from `PrinterCapabilityEligibilityChecker`.

## Checker-Specific Examples

### InventoryEligibilityChecker example

The job requires `PETG + black + 1.75 mm + 120 g`.

The printer is technically compatible, but the only matching spool has `80 g` available.

```json
{
  "checker": "InventoryEligibilityChecker",
  "eligible": false,
  "failures": [
    {
      "code": "inventory_material_insufficient",
      "requirement": "job.requirements.material.amount_g",
      "detail": {
        "required_g": 120,
        "best_available_g": 80,
        "matching_spool_id": "spool-123"
      }
    }
  ]
}
```

### PrinterOperationalEligibilityChecker example

The printer is fully capable, and inventory has a matching spool, but the printer is in maintenance mode.

```json
{
  "checker": "PrinterOperationalEligibilityChecker",
  "eligible": false,
  "failures": [
    {
      "code": "printer_in_maintenance",
      "requirement": "printer.operational_state",
      "detail": {
        "state": "maintenance"
      }
    }
  ]
}
```

### Combined orchestrator example

The combined eligibility result should preserve the source of failures while still returning one final answer to the scheduler.

```json
{
  "eligible": false,
  "failures": [
    {
      "code": "inventory_material_insufficient",
      "requirement": "job.requirements.material.amount_g",
      "detail": {
        "required_g": 120,
        "best_available_g": 80,
        "matching_spool_id": "spool-123"
      }
    },
    {
      "code": "printer_in_maintenance",
      "requirement": "printer.operational_state",
      "detail": {
        "state": "maintenance"
      }
    }
  ]
}
```
