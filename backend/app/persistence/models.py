from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    scheduling: Mapped["JobSchedulingRecord"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )


class JobSchedulingRecord(Base):
    __tablename__ = "job_scheduling"

    job_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("jobs.id"), primary_key=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    printer_assignment_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_printer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job: Mapped[JobRecord] = relationship(back_populates="scheduling")
    tags: Mapped[list["JobSchedulingTagRecord"]] = relationship(
        back_populates="scheduling",
        cascade="all, delete-orphan",
        order_by="JobSchedulingTagRecord.position",
    )


class JobSchedulingTagRecord(Base):
    __tablename__ = "job_scheduling_tags"

    job_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("job_scheduling.job_id"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String(255), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduling: Mapped[JobSchedulingRecord] = relationship(back_populates="tags")


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
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_metadata_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False
    )
