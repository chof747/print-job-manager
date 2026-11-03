from dataclasses import dataclass
from datetime import date


def filter_queue_jobs(
    result: dict[str, list[object]],
    material: str | None,
    min_duration_seconds: int | None,
    min_priority: int | None,
) -> dict[str, list[object]]:
    if material is not None:
        result["jobs"] = [
            job
            for job in result["jobs"]
            if isinstance(job, dict)
            and isinstance(job.get("executionData"), dict)
            and job["executionData"].get("material") == material
        ]
    if min_duration_seconds is not None:
        filtered: list[object] = []
        for job in result["jobs"]:
            if not isinstance(job, dict):
                continue
            execution_data = job.get("executionData")
            if not isinstance(execution_data, dict):
                continue
            metadata = execution_data.get("extractedMetadata")
            if not isinstance(metadata, dict):
                continue
            duration = metadata.get("estimatedDuration")
            if isinstance(duration, (int, float)) and duration >= min_duration_seconds:
                filtered.append(job)
        result["jobs"] = filtered
    if min_priority is not None:
        result["jobs"] = [
            job
            for job in result["jobs"]
            if isinstance(job, dict)
            and isinstance(job.get("schedulingData"), dict)
            and isinstance(job["schedulingData"].get("priority"), int)
            and job["schedulingData"]["priority"] >= min_priority
        ]
    return result


@dataclass(frozen=True, kw_only=True)
class CockpitFilters:
    diagnostic_code: str | None = None
    material: str | None = None
    min_duration_seconds: int | None = None
    min_priority: int | None = None
    due_before: date | None = None
    tag: str | None = None
    assignment_mode: str | None = None
    max_filament_weight_grams: float | None = None
    nozzle_diameter: float | None = None
    max_dimension_x: float | None = None
    max_dimension_y: float | None = None
    max_dimension_z: float | None = None
    slicer: str | None = None
    provenance_parser: str | None = None


def project_cockpit(
    cockpit_jobs: list[dict[str, object]],
    filters: CockpitFilters,
) -> dict[str, list[dict[str, object]]]:
    result = filter_queue_jobs(
        {"jobs": list(cockpit_jobs)},
        filters.material, filters.min_duration_seconds, filters.min_priority,
    )
    jobs = [job for job in result["jobs"] if isinstance(job, dict)]
    if any(value is not None for value in (filters.max_filament_weight_grams, filters.nozzle_diameter, filters.max_dimension_x, filters.max_dimension_y, filters.max_dimension_z, filters.slicer)):
        characteristic_jobs = []
        for job in jobs:
            execution = job.get("executionData")
            if not isinstance(execution, dict):
                continue
            metadata = execution.get("extractedMetadata")
            if not isinstance(metadata, dict):
                metadata = {}
            weight = metadata.get("filamentWeightGrams")
            if filters.max_filament_weight_grams is not None and (
                not isinstance(weight, (int, float)) or weight > filters.max_filament_weight_grams
            ):
                continue
            if filters.nozzle_diameter is not None and execution.get("nozzleDiameter") != filters.nozzle_diameter:
                continue
            dimensions = metadata.get("dimensions")
            dimension_x = dimensions.get("x") if isinstance(dimensions, dict) else None
            if filters.max_dimension_x is not None and (
                not isinstance(dimension_x, (int, float)) or dimension_x > filters.max_dimension_x
            ):
                continue
            dimension_y = dimensions.get("y") if isinstance(dimensions, dict) else None
            if filters.max_dimension_y is not None and (
                not isinstance(dimension_y, (int, float)) or dimension_y > filters.max_dimension_y
            ):
                continue
            dimension_z = dimensions.get("z") if isinstance(dimensions, dict) else None
            if filters.max_dimension_z is not None and (
                not isinstance(dimension_z, (int, float)) or dimension_z > filters.max_dimension_z
            ):
                continue
            if filters.slicer is not None and metadata.get("slicer") != filters.slicer:
                continue
            characteristic_jobs.append(job)
        jobs = characteristic_jobs
    if filters.due_before is not None or filters.tag is not None or filters.assignment_mode is not None:
        filtered_jobs = []
        for job in jobs:
            scheduling = job.get("schedulingData")
            if not isinstance(scheduling, dict):
                continue
            due_date = scheduling.get("dueDate")
            if filters.due_before is not None and (
                not isinstance(due_date, str) or due_date > filters.due_before.isoformat()
            ):
                continue
            tags = scheduling.get("tags")
            if filters.tag is not None and (not isinstance(tags, list) or filters.tag not in tags):
                continue
            assignment = scheduling.get("printerAssignment")
            if filters.assignment_mode == "unassigned":
                if assignment is not None:
                    continue
            elif filters.assignment_mode is not None and (
                not isinstance(assignment, dict) or assignment.get("mode") != filters.assignment_mode
            ):
                continue
            filtered_jobs.append(job)
        jobs = filtered_jobs
    if filters.diagnostic_code is not None:
        jobs = [
            job for job in jobs
            if isinstance(job.get("parsedMetadataSnapshot"), dict)
            and any(
                isinstance(diagnostic, dict) and diagnostic.get("code") == filters.diagnostic_code
                for diagnostic in job["parsedMetadataSnapshot"].get("diagnostics", [])
            )
        ]
    if filters.provenance_parser is not None:
        provenance_jobs = []
        for job in jobs:
            snapshot = job.get("parsedMetadataSnapshot")
            provenance = snapshot.get("provenance") if isinstance(snapshot, dict) else None
            if isinstance(provenance, dict) and any(
                isinstance(source, dict) and source.get("parser") == filters.provenance_parser
                for source in provenance.values()
            ):
                provenance_jobs.append(job)
        jobs = provenance_jobs
    return {
        "activeJobs": [job for job in jobs if job["state"] == "ready"],
        "failures": [job for job in jobs if job["state"] == "failed"],
        "recentHistory": [
            job for job in jobs
            if job["state"] in {"failed", "completed", "cancelled", "archived"}
        ][:20],
    }
