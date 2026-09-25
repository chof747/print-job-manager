from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .database import SessionFactory
from .models import ArtifactRecord, JobHistoryRecord, JobRecord


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
            statement = (
                insert(JobRecord)
                .values(
                    id=job["id"],
                    artifact_ref=artifact_ref,
                    parsed_metadata_snapshot=deepcopy(
                        artifact.parsed_metadata_snapshot
                    ),
                    state=job["state"],
                    execution_data=deepcopy(execution_data),
                    scheduling_data=deepcopy(job["schedulingData"]),
                )
                .on_conflict_do_nothing(index_elements=[JobRecord.artifact_ref])
                .returning(JobRecord.id)
            )
            created = session.scalar(statement) is not None
            record = session.scalar(
                select(JobRecord).where(JobRecord.artifact_ref == artifact_ref)
            )
            if record is None:
                raise RuntimeError("job insert did not return a record")
            if created:
                job_id = creation_history["jobId"]
                state = creation_history["state"]
                if not isinstance(job_id, str) or not isinstance(state, str):
                    raise TypeError(
                        "creation history must contain string jobId and state"
                    )
                session.add(
                    JobHistoryRecord(id=f"{job_id}-{state}", job_id=job_id, state=state)
                )
            return self._as_job(record), created

    def active_queue(self) -> dict[str, list[object]]:
        with SessionFactory() as session:
            records = session.scalars(
                select(JobRecord)
                .where(JobRecord.state == "ready")
                .order_by(JobRecord.queue_position)
            )
            return {"jobs": [self._as_job(record) for record in records]}

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with SessionFactory() as session:
            record = session.get(JobRecord, job_id)
            return self._as_job(record) if record is not None else None

    @staticmethod
    def _as_job(record: JobRecord) -> dict[str, object]:
        return {
            "id": record.id,
            "state": record.state,
            "executionData": deepcopy(record.execution_data),
            "schedulingData": deepcopy(record.scheduling_data),
        }
