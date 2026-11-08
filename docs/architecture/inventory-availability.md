# MVP inventory availability

The MVP eligibility evaluator asks an inventory availability boundary whether
material matching a job's requirements is available. Jobs describe material
attributes, not a particular spool ([ADR-0003](../adr/0003-jobs-reference-material-attributes.md)).
The current boundary is backed by the local `inventory_materials` table; this
does not decide the source of truth for a future Spoolman integration.

## Current local behavior

Each record has a local ID, material type, color and amount in grams. Material
type and, when requested, color are matched exactly. A matching record must
have a positive amount and, when an amount is requested, that single record
must contain at least that amount. Amounts across records are not summed: two
matching records with 60 g each do not satisfy a 100 g requirement. A record's
amount can be corrected, including to zero.

The schema does not establish whether a record represents a physical spool or
an aggregate of material. In particular, it has no external resource identity.
Do not assume either interpretation is a settled domain decision. The meaning
of a record and whether the single-record rule remains appropriate need to be
resolved as inventory and Spoolman integration are designed in
[epic #18](https://github.com/chof747/print-job-manager/issues/18).

The availability interface can also return an unverified result, which the
eligibility evaluator treats as blocked rather than as confirmed availability.
The current local implementation returns available or unavailable; it does not
implement Spoolman synchronization or a freshness policy.

## Availability is not reservation

The current availability check is a read, not a reservation. The accepted
policy in [ADR-0014](../adr/0014-check-inventory-at-assignment-time.md) requires
checking availability before assignment and reserving a concrete inventory
resource when an assignment is created. Reservation, release and consumption
reconciliation require additional implementation; this table and check alone
do not provide them.

Epic #18 tracks the future source-of-truth, synchronization, stale-data and
resource-mapping decisions. An integration must account for the assignment
reservation policy without binding the job definition permanently to a spool.
