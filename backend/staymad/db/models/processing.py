"""ProcessingRun and ProcessingJob models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base, JSONType
from backend.staymad.db.models.enums import (
    JobStatus,
    JobType,
    ProcessingStage,
    RunStatus,
)


class ProcessingRun(Base):
    """Provenance tracking for execution batches and pipeline stages.

    Authority: docs/architecture/B-data-model.md §2.14, Addendum §9
    """

    __tablename__ = "processing_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage, name="processing_stage_enum"),
        nullable=False,
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status_enum"),
        nullable=False,
        default=RunStatus.RUNNING,
    )
    articles_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_estimate_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    jobs: Mapped[list[ProcessingJob]] = relationship(
        "ProcessingJob",
        back_populates="processing_run",
        cascade="all, delete-orphan",
    )


class ProcessingJob(Base):
    """Asynchronous background work queue unit.

    Authority: docs/architecture/B-data-model.md §2.15, Master Spec §38
    """

    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("processing_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_type_enum"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    processing_run: Mapped[ProcessingRun] = relationship(
        "ProcessingRun", back_populates="jobs"
    )

    __table_args__ = (
        Index("idx_job_idempotency_key", "idempotency_key"),
        Index("idx_job_correlation_id", "correlation_id"),
    )
