"""Location entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import GeoLevel

if TYPE_CHECKING:
    from backend.staymad.db.models.event import Event


class Location(Base):
    """Geographic location reference model.

    Authority: docs/architecture/B-data-model.md §2.5
    """

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    province: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Indonesia"
    )
    continent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_level: Mapped[GeoLevel] = mapped_column(
        Enum(GeoLevel, name="geo_level_enum"),
        nullable=False,
    )
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    events: Mapped[list[Event]] = relationship(
        "Event", back_populates="primary_location"
    )
