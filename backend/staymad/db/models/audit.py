"""EventMembershipAudit entity model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.staymad.db.base import Base, JSONType
from backend.staymad.db.models.enums import ResolutionDecision

if TYPE_CHECKING:
    from backend.staymad.db.models.article import ArticleVersion
    from backend.staymad.db.models.processing import ProcessingRun


class EventMembershipAudit(Base):
    """Audit record capturing event membership resolution reasoning.

    Authority: docs/architecture/B-data-model.md §2.10, Addendum §6
    """

    __tablename__ = "event_membership_audits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    article_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("article_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_event_ids: Mapped[list[Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )
    decision: Mapped[ResolutionDecision] = mapped_column(
        Enum(ResolutionDecision, name="resolution_decision_enum"),
        nullable=False,
    )
    deterministic_signals: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )
    decision_reason_codes: Mapped[list[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )
    evidence_claim_ids: Mapped[list[Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
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
    article_version: Mapped[ArticleVersion] = relationship(
        "ArticleVersion", back_populates="membership_audits"
    )
    processing_run: Mapped[ProcessingRun] = relationship("ProcessingRun")
