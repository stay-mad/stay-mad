"""Event, EventSnapshot, EventChange, and EventClaim models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

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
    ActionabilityLevel,
    ChangeCategory,
    ChangeType,
    ConfidenceBucket,
    DataMode,
    EventCategory,
    EventClaimRole,
    EvidenceStatus,
    VerificationLevel,
)

if TYPE_CHECKING:
    from backend.staymad.db.models.action import Action
    from backend.staymad.db.models.claim import Claim
    from backend.staymad.db.models.conflict import Conflict
    from backend.staymad.db.models.location import Location
    from backend.staymad.db.models.processing import ProcessingRun
    from backend.staymad.db.models.timeline import TimelineEntry


class Event(Base):
    """Canonical Event entity.

    Authority: docs/architecture/B-data-model.md §2.6
    """

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[EventCategory] = mapped_column(
        Enum(EventCategory, name="event_category_enum"),
        nullable=False,
    )
    primary_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    time_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    time_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    primary_location: Mapped[Location | None] = relationship(
        "Location", back_populates="events"
    )
    snapshots: Mapped[list[EventSnapshot]] = relationship(
        "EventSnapshot",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventSnapshot.version_number",
    )
    changes: Mapped[list[EventChange]] = relationship(
        "EventChange",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    event_claims: Mapped[list[EventClaim]] = relationship(
        "EventClaim",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    timeline_entries: Mapped[list[TimelineEntry]] = relationship(
        "TimelineEntry",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    conflicts: Mapped[list[Conflict]] = relationship(
        "Conflict",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    actions: Mapped[list[Action]] = relationship(
        "Action",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_event_category", "category"),
        Index("idx_event_location", "primary_location_id", "time_window_start"),
    )


class EventSnapshot(Base):
    """Immutable published snapshot of an event at a point in time.

    Authority: docs/architecture/B-data-model.md §2.7, Addendum §4
    """

    __tablename__ = "event_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    what_happened_evidence_claim_ids: Mapped[list[str]] = mapped_column(
        JSONType, nullable=True, default=list
    )
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONType, nullable=True, default=list
    )
    who_is_affected: Mapped[str | None] = mapped_column(Text, nullable=True)
    who_is_affected_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONType, nullable=True, default=list
    )
    what_is_unknown: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_summary_evidence_claim_ids: Mapped[list[str] | None] = mapped_column(
        JSONType, nullable=True, default=list
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_bucket: Mapped[ConfidenceBucket] = mapped_column(
        Enum(ConfidenceBucket, name="confidence_bucket_enum"),
        nullable=False,
    )
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status_enum"),
        nullable=False,
    )
    verification_level: Mapped[VerificationLevel] = mapped_column(
        Enum(VerificationLevel, name="verification_level_enum"),
        nullable=False,
    )
    actionability_level: Mapped[ActionabilityLevel] = mapped_column(
        Enum(ActionabilityLevel, name="actionability_level_enum"),
        nullable=False,
    )
    importance_score: Mapped[float] = mapped_column(Float, nullable=False)
    urgency_score: Mapped[float] = mapped_column(Float, nullable=False)
    data_mode: Mapped[DataMode] = mapped_column(
        Enum(DataMode, name="data_mode_enum"),
        nullable=False,
        default=DataMode.LIVE,
    )
    last_processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("processing_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="snapshots")
    processing_run: Mapped[ProcessingRun] = relationship("ProcessingRun")
    timeline_entries: Mapped[list[TimelineEntry]] = relationship(
        "TimelineEntry", back_populates="snapshot", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("what_happened_evidence_claim_ids", [])
        kwargs.setdefault("why_it_matters_evidence_claim_ids", [])
        kwargs.setdefault("who_is_affected_evidence_claim_ids", [])
        kwargs.setdefault("conflict_summary_evidence_claim_ids", [])
        super().__init__(**kwargs)

    __table_args__ = (Index("idx_processing_run_id_snapshot", "processing_run_id"),)


class EventChange(Base):
    """Structured delta between snapshots.

    Authority: docs/architecture/B-data-model.md §2.8, Addendum §7
    """

    __tablename__ = "event_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("event_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("event_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(ChangeType, name="change_type_enum"),
        nullable=False,
    )
    change_category: Mapped[ChangeCategory | None] = mapped_column(
        Enum(ChangeCategory, name="change_category_enum"),
        nullable=True,
    )
    field_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_claim_ids: Mapped[list[Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="changes")
    from_snapshot: Mapped[EventSnapshot | None] = relationship(
        "EventSnapshot", foreign_keys=[from_snapshot_id]
    )
    to_snapshot: Mapped[EventSnapshot] = relationship(
        "EventSnapshot", foreign_keys=[to_snapshot_id]
    )


class EventClaim(Base):
    """Join entity linking claims to events and snapshots with designated roles.

    Authority: docs/architecture/B-data-model.md §2.9
    """

    __tablename__ = "event_claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("event_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[EventClaimRole] = mapped_column(
        Enum(EventClaimRole, name="event_claim_role_enum"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="event_claims")
    claim: Mapped[Claim] = relationship("Claim", back_populates="event_claims")
