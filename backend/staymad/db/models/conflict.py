"""Conflict entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim
    from backend.staymad.db.models.event import Event, EventSnapshot


class Conflict(Base):
    """Explicit record of conflicting claims on factual fields.

    Authority: docs/architecture/B-data-model.md §2.12, Addendum §5
    """

    __tablename__ = "conflicts"

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
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    claim_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    value_a: Mapped[str] = mapped_column(Text, nullable=False)
    value_b: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="conflicts")
    snapshot: Mapped[EventSnapshot] = relationship("EventSnapshot")
    claim_a: Mapped[Claim] = relationship("Claim", foreign_keys=[claim_a_id])
    claim_b: Mapped[Claim] = relationship("Claim", foreign_keys=[claim_b_id])
    resolution_claim: Mapped[Claim | None] = relationship(
        "Claim", foreign_keys=[resolution_claim_id]
    )
