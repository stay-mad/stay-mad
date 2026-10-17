"""EventRelation entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import EventRelationType

if TYPE_CHECKING:
    from backend.staymad.db.models.event import Event
    from backend.staymad.db.models.processing import ProcessingRun


class EventRelation(Base):
    """Inter-event relation graph model (MVP: related_to).

    Authority: docs/architecture/B-data-model.md §2.16, ADR-003
    """

    __tablename__ = "event_relations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    from_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[EventRelationType] = mapped_column(
        Enum(EventRelationType, name="event_relation_type_enum"),
        nullable=False,
        default=EventRelationType.RELATED_TO,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("processing_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    from_event: Mapped[Event] = relationship("Event", foreign_keys=[from_event_id])
    to_event: Mapped[Event] = relationship("Event", foreign_keys=[to_event_id])
    processing_run: Mapped[ProcessingRun] = relationship("ProcessingRun")
