"""Source entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import SourceTier, SourceType

if TYPE_CHECKING:
    from backend.staymad.db.models.article import Article
    from backend.staymad.db.models.claim import Claim


class Source(Base):
    """Source represents an authorized data feed or publishing origin.

    Authority: docs/architecture/B-data-model.md §2.1, docs/sources.md
    """

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"),
        nullable=False,
    )
    source_tier: Mapped[SourceTier] = mapped_column(
        Enum(SourceTier, name="source_tier_enum"),
        nullable=False,
    )
    source_family: Mapped[str] = mapped_column(String(100), nullable=False)
    robots_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    retention_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    articles: Mapped[list[Article]] = relationship("Article", back_populates="source")
    claims: Mapped[list[Claim]] = relationship("Claim", back_populates="source")
