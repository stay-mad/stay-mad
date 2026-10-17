"""Claim entity model with pgvector 768 embeddings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import TimelinePrecision

if TYPE_CHECKING:
    from backend.staymad.db.models.article import ArticleVersion
    from backend.staymad.db.models.event import EventClaim
    from backend.staymad.db.models.processing import ProcessingRun
    from backend.staymad.db.models.source import Source


class Claim(Base):
    """Atomic factual claim extracted from an article version.

    Authority: docs/architecture/B-data-model.md §2.4, Addendum §9 (append-only)
    Contains 768-dimensional pgvector embedding for Tier-2 retrieval (ADR-007).
    """

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    article_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("article_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_span: Mapped[str] = mapped_column(String(200), nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    negation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_time_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    event_time_precision: Mapped[TimelinePrecision] = mapped_column(
        Enum(TimelinePrecision, name="timeline_precision_enum"),
        nullable=False,
    )
    event_time_qualifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="id")
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("processing_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    article_version: Mapped[ArticleVersion] = relationship(
        "ArticleVersion", back_populates="claims"
    )
    source: Mapped[Source] = relationship("Source", back_populates="claims")
    processing_run: Mapped[ProcessingRun] = relationship("ProcessingRun")
    event_claims: Mapped[list[EventClaim]] = relationship(
        "EventClaim", back_populates="claim"
    )

    __table_args__ = (
        Index("idx_claim_event_time", "event_time"),
        Index("idx_processing_run_id", "processing_run_id"),
    )
