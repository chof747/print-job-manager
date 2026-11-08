"""Evaluate job eligibility against trusted printer and inventory facts."""

import math
from typing import Protocol


class InventoryAvailability(Protocol):
    def is_available(self, material_type: str, color: str | None = ..., amount_grams: float | None = ...) -> bool | None: ...


def evaluate_eligibility(
    job: dict[str, object], printer_id: str, printer: dict[str, object] | None,
    inventory: InventoryAvailability,
) -> dict[str, object]:
    if not isinstance(printer, dict) or printer.get("id") != printer_id:
        return {"eligible": False, "blocked": True, "failures": [{"code": "printer_capabilities_unverified"}], "satisfied": []}
    execution = job.get("executionData", {})
    requirements = execution.get("requirements", {})
    failures = []
    satisfied = []
    material = execution.get("material")
    material_requirement = requirements.get("material")
    extracted = execution.get("extractedMetadata", {})
    extracted_amount = extracted.get("filamentWeightGrams") if isinstance(extracted, dict) else None
    if not isinstance(material, str):
        available = None
    elif isinstance(material_requirement, dict):
        required_amount = material_requirement.get("amountGrams")
        if extracted_amount is not None:
            required_amount = max(extracted_amount, required_amount) if required_amount is not None else extracted_amount
        available = inventory.is_available(
            material, material_requirement.get("color"), required_amount,
        )
    elif extracted_amount is not None:
        available = inventory.is_available(material, amount_grams=extracted_amount)
    else:
        available = inventory.is_available(material)
    if available is False:
        failures.append({"code": "inventory_material_unavailable"})
    elif available is not True:
        failures.append({"code": "inventory_unverified"})
    else:
        satisfied.append({"code": "material_satisfied"})
    if requirements.get("enclosure") is True and printer.get("enclosure") is not True:
        failures.append({"code": "enclosure_required"})
    elif requirements.get("enclosure") is True:
        satisfied.append({"code": "enclosure_satisfied"})
    if requirements.get("hardenedNozzle") is True and printer.get("hardenedNozzle") is not True:
        failures.append({"code": "hardened_nozzle_required"})
    elif requirements.get("hardenedNozzle") is True:
        satisfied.append({"code": "hardened_nozzle_satisfied"})
    nozzle = execution.get("nozzleDiameter")
    if nozzle is not None and printer.get("nozzleDiameter") != nozzle:
        failures.append({"code": "nozzle_diameter_mismatch"})
    elif nozzle is not None:
        satisfied.append({"code": "nozzle_diameter_satisfied"})
    dimensions = extracted.get("dimensions") if isinstance(extracted, dict) else None
    declared_volume = requirements.get("buildVolume")
    if isinstance(declared_volume, dict):
        dimensions = (
            {axis: max(dimensions[axis], declared_volume[axis]) for axis in ("x", "y", "z")}
            if isinstance(dimensions, dict) else declared_volume
        )
    if isinstance(dimensions, dict):
        volume = printer.get("buildVolume")
        if not isinstance(volume, dict) or any(
            not isinstance(volume.get(axis), (int, float))
            or isinstance(volume[axis], bool)
            or not math.isfinite(volume[axis])
            or volume[axis] < dimensions[axis]
            for axis in ("x", "y", "z")
        ):
            failures.append({"code": "build_volume_exceeded"})
        else:
            satisfied.append({"code": "build_volume_satisfied"})
    scheduling = job.get("schedulingData", {})
    assignment = scheduling.get("printerAssignment") if isinstance(scheduling, dict) else None
    if isinstance(assignment, dict) and assignment.get("mode") == "required" and printer.get("id") != assignment.get("printerId"):
        failures.append({"code": "required_printer_mismatch"})
    elif isinstance(assignment, dict) and assignment.get("mode") == "required":
        satisfied.append({"code": "required_printer_satisfied"})
    return {"eligible": not failures, "blocked": bool(failures), "failures": failures, "satisfied": satisfied}
