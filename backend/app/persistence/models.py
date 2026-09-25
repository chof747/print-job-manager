from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artifact_ref: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id"), unique=True, nullable=False
    )
    parsed_metadata_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    execution_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    scheduling_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    queue_position: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), unique=True, nullable=False
    )


class JobHistoryRecord(Base):
    __tablename__ = "job_history"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("jobs.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArtifactRecord(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_metadata_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False
    )
