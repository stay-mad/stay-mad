"""Article and ArticleVersion models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import EventCategory

if TYPE_CHECKING:
    from backend.staymad.db.models.audit import EventMembershipAudit
    from backend.staymad.db.models.claim import Claim
    from backend.staymad.db.models.processing import ProcessingRun
    from backend.staymad.db.models.source import Source


class Article(Base):
    """Canonical Article entity with deduplication content hash.

    Authority: docs/architecture/B-data-model.md §2.2
    """

    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    category: Mapped[EventCategory] = mapped_column(
        Enum(EventCategory, name="event_category_enum"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="id")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    source: Mapped[Source] = relationship("Source", back_populates="articles")
    versions: Mapped[list[ArticleVersion]] = relationship(
        "ArticleVersion",
        back_populates="article",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_article_content_hash", "content_hash", unique=True),)


class ArticleVersion(Base):
    """Immutable ArticleVersion snapshot representing article state at fetch time.

    Authority: docs/architecture/B-data-model.md §2.3, Addendum §4
    """

    __tablename__ = "article_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    fetch_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    published_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    excerpt: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    full_text_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    schema_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0",
    )
    processing_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("processing_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    article: Mapped[Article] = relationship("Article", back_populates="versions")
    processing_run: Mapped[ProcessingRun | None] = relationship("ProcessingRun")
    claims: Mapped[list[Claim]] = relationship(
        "Claim",
        back_populates="article_version",
        cascade="all, delete-orphan",
    )
    membership_audits: Mapped[list[EventMembershipAudit]] = relationship(
        "EventMembershipAudit",
        back_populates="article_version",
    )
