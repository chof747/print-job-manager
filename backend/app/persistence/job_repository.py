from copy import deepcopy
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .database import SessionFactory
from .extraction_projection import extraction_facts
from .models import (
    ArtifactExtraction,
    ArtifactRecord,
    JobHistoryRecord,
    JobRecord,
    JobSchedulingRecord,
    JobSchedulingTagRecord,
)


class SchedulingVersionConflict(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version


class SqlAlchemyJobRepository:
    """PostgreSQL authority for ready jobs and the active queue projection."""

    def create_ready_job(
        self, *, job: dict[str, object], creation_history: dict[str, object]
    ) -> tuple[dict[str, object], bool]:
        execution_data = job["executionData"]
        if not isinstance(execution_data, dict):
            raise TypeError("executionData must be an object")
        artifact_ref = execution_data["artifactRef"]
        if not isinstance(artifact_ref, str):
            raise TypeError("executionData.artifactRef must be a string")

        with SessionFactory.begin() as session:
            artifact = session.get(ArtifactRecord, artifact_ref)
            if artifact is None:
                raise RuntimeError("job artifact does not exist")
            extraction_id = job.get("_extraction_id")
            if extraction_id is not None:
                if not isinstance(extraction_id, str):
                    raise TypeError("extraction id must be a string")
                extraction = session.get(ArtifactExtraction, extraction_id)
                if extraction is not None and extraction.artifact_id != artifact_ref:
                    raise RuntimeError("artifact extraction does not belong to job artifact")
            else:
                extraction = session.scalar(
                    select(ArtifactExtraction).where(
                        ArtifactExtraction.artifact_id == artifact_ref

                    )
                )
            if extraction is None:
                raise RuntimeError("artifact extraction does not exist")
            parsed = extraction_facts(session, artifact, extraction)
            record = JobRecord(
                id=job["id"],
                artifact_ref=artifact_ref,
                extraction_id=extraction.id,
                parsed_metadata_snapshot=parsed,
                state=job["state"],
                execution_data=deepcopy(execution_data),
                scheduling_data=deepcopy(job["schedulingData"]),
            )
            record.scheduling = JobSchedulingRecord(priority=record.priority)
            session.add(record)
            session.flush()
            job_id = creation_history["jobId"]
            state = creation_history["state"]
            if not isinstance(job_id, str) or not isinstance(state, str):
                raise TypeError("creation history must contain string jobId and state")
            session.add(
                JobHistoryRecord(id=f"{job_id}-{state}", job_id=job_id, state=state)
            )
            return self._as_job(record), True

    def active_queue(self) -> dict[str, list[object]]:
        with SessionFactory() as session:
            records = session.scalars(
                select(JobRecord)
                .where(JobRecord.state == "ready")
                .options(
                    selectinload(JobRecord.scheduling).selectinload(
                        JobSchedulingRecord.tags
                    )
                )
                .order_by(JobRecord.queue_position)
            )
            return {"jobs": [self._as_job(record) for record in records]}

    def cockpit_jobs(self) -> list[dict[str, object]]:
        with SessionFactory() as session:
            terminal_time = (
                select(func.max(JobHistoryRecord.created_at))
                .where(
                    JobHistoryRecord.job_id == JobRecord.id,
                    JobHistoryRecord.state.in_(("failed", "completed", "cancelled", "archived")),
                )
                .scalar_subquery()
            )
            records = session.scalars(
                select(JobRecord)
                .options(
                    selectinload(JobRecord.scheduling).selectinload(
                        JobSchedulingRecord.tags
                    )
                )
                .order_by(terminal_time.desc().nullslast(), JobRecord.queue_position)
            )
            return [self._as_job(record) for record in records]

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with SessionFactory() as session:
            record = session.scalar(
                select(JobRecord)
                .where(JobRecord.id == job_id)
                .options(
                    selectinload(JobRecord.scheduling).selectinload(
                        JobSchedulingRecord.tags
                    )
                )
            )
            return self._as_job(record) if record is not None else None

    def update_scheduling(
        self,
        *,
        job_id: str,
        scheduling_data: dict[str, object],
        expected_version: int | None,
    ) -> dict[str, object] | None:
        with SessionFactory.begin() as session:
            record = session.scalar(
                select(JobRecord)
                .where(JobRecord.id == job_id)
                .with_for_update()
                .options(
                    selectinload(JobRecord.scheduling).selectinload(
                        JobSchedulingRecord.tags
                    )
                )
            )
            if record is None:
                return None
            scheduling = record.scheduling
            if (
                expected_version is not None
                and expected_version != scheduling.version
            ):
                raise SchedulingVersionConflict(scheduling.version)
            if "priority" in scheduling_data:
                priority = scheduling_data["priority"]
                if not isinstance(priority, int):
                    raise TypeError("schedulingData.priority must be an integer")
                scheduling.priority = priority
                record.priority = priority
            if "dueDate" in scheduling_data:
                due_date = scheduling_data["dueDate"]
                if due_date is not None and not isinstance(due_date, date):
                    raise TypeError("schedulingData.dueDate must be a date")
                scheduling.due_date = due_date
            if "notes" in scheduling_data:
                notes = scheduling_data["notes"]
                if notes is not None and not isinstance(notes, str):
                    raise TypeError("schedulingData.notes must be a string")
                scheduling.notes = notes
            if "tags" in scheduling_data:
                tags = scheduling_data["tags"]
                if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                    raise TypeError("schedulingData.tags must be a list of strings")
                scheduling.tags = [
                    JobSchedulingTagRecord(tag=tag, position=position)
                    for position, tag in enumerate(tags)
                ]
            if "printerAssignment" in scheduling_data:
                assignment = scheduling_data["printerAssignment"]
                if assignment is None:
                    scheduling.printer_assignment_mode = None
                    scheduling.preferred_printer_id = None
                elif isinstance(assignment, dict):
                    mode = assignment.get("mode")
                    printer_id = assignment.get("printerId")
                    if mode not in ("preferred", "required") or not isinstance(printer_id, str):
                        raise TypeError("printer assignment must be a preferred or required printer")
                    scheduling.printer_assignment_mode = mode
                    scheduling.preferred_printer_id = printer_id
                else:
                    raise TypeError("schedulingData.printerAssignment must be an object")
            scheduling.version += 1
            session.flush()
            return self._as_job(record)

    @staticmethod
    def _as_job(record: JobRecord) -> dict[str, object]:
        scheduling_data: dict[str, object] = {"priority": record.scheduling.priority}
        if record.scheduling.due_date is not None:
            scheduling_data["dueDate"] = record.scheduling.due_date.isoformat()
        if record.scheduling.notes is not None:
            scheduling_data["notes"] = record.scheduling.notes
        if record.scheduling.tags:
            scheduling_data["tags"] = [tag.tag for tag in record.scheduling.tags]
        if record.scheduling.printer_assignment_mode is not None:
            scheduling_data["printerAssignment"] = {
                "mode": record.scheduling.printer_assignment_mode,
                "printerId": record.scheduling.preferred_printer_id,
            }
        return {
            "id": record.id,
            "state": record.state,
            "version": record.scheduling.version,
            "parsedMetadataSnapshot": deepcopy(record.parsed_metadata_snapshot),
            "executionData": deepcopy(record.execution_data),
            "schedulingData": scheduling_data,
        }
