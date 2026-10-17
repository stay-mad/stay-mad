"""TimelineEntry entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base, JSONType
from backend.staymad.db.models.enums import TimelinePrecision

if TYPE_CHECKING:
    from backend.staymad.db.models.event import Event, EventSnapshot


class TimelineEntry(Base):
    """Chronological timeline entry associated with an event snapshot.

    Authority: docs/architecture/B-data-model.md §2.11, §53-E
    """

    __tablename__ = "timeline_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("event_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    event_time_precision: Mapped[TimelinePrecision] = mapped_column(
        Enum(TimelinePrecision, name="timeline_precision_enum"),
        nullable=False,
    )
    event_time_qualifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_claim_ids: Mapped[list[Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="timeline_entries")
    snapshot: Mapped[EventSnapshot] = relationship(
        "EventSnapshot", back_populates="timeline_entries"
    )
