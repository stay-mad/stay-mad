"""Audit Trail generation and persistence for Event Membership decisions.

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D §5), docs/architecture/B-data-model.md §2.10
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.staymad.db.models.audit import EventMembershipAudit
from backend.staymad.db.models.enums import ResolutionDecision


def create_and_persist_membership_audit(
    session: Session,
    article_version_id: uuid.UUID,
    candidate_event_ids: list[str | uuid.UUID],
    decision: str | ResolutionDecision,
    deterministic_signals: dict[str, Any],
    decision_reason_codes: list[str],
    evidence_claim_ids: list[str | uuid.UUID],
    model_version: str,
    prompt_version: str,
    schema_version: str,
    processing_run_id: uuid.UUID,
    tier_used: str,
) -> EventMembershipAudit:
    """Create and persist an EventMembershipAudit record capturing decision rationale and tier used."""
    if isinstance(decision, str):
        dec_enum = ResolutionDecision(decision)
    else:
        dec_enum = decision

    signals = dict(deterministic_signals)
    signals["tier_used"] = tier_used

    audit_entry = EventMembershipAudit(
        id=uuid.uuid4(),
        article_version_id=article_version_id,
        candidate_event_ids=[str(cid) for cid in candidate_event_ids],
        decision=dec_enum,
        deterministic_signals=signals,
        decision_reason_codes=decision_reason_codes,
        evidence_claim_ids=[str(cid) for cid in evidence_claim_ids],
        model_version=model_version,
        prompt_version=prompt_version,
        schema_version=schema_version,
        processing_run_id=processing_run_id,
    )
    session.add(audit_entry)
    return audit_entry
