"""Action entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base, JSONType
from backend.staymad.db.models.enums import ActionabilityLevel, ActionSourceType

if TYPE_CHECKING:
    from backend.staymad.db.models.event import Event, EventSnapshot


class Action(Base):
    """Action recommendation gated by authority policy.

    Authority: docs/architecture/B-data-model.md §2.13, ADR-006 (§53-H)
    evidence_claim_ids is mandatory for ACTION_REQUIRED and ACTION_RECOMMENDED.
    """

    __tablename__ = "actions"

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
    action_level: Mapped[ActionabilityLevel] = mapped_column(
        Enum(ActionabilityLevel, name="actionability_level_enum"),
        nullable=False,
    )
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[ActionSourceType] = mapped_column(
        Enum(ActionSourceType, name="action_source_type_enum"),
        nullable=False,
    )
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
    event: Mapped[Event] = relationship("Event", back_populates="actions")
    snapshot: Mapped[EventSnapshot] = relationship("EventSnapshot")
