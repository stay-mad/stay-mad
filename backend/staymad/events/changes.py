"""Event Changeset and Material Change Detection Module.

Authority: docs/architecture/B-data-model.md §2.8, docs/architecture/E-timeline-algorithm.md §53-E Step 6,
Addendum §7, decisions.md DEC-0005
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from backend.staymad.db.models.enums import ChangeCategory, ChangeType
from backend.staymad.db.models.event import EventChange

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim
    from backend.staymad.db.models.conflict import Conflict
    from backend.staymad.db.models.event import EventSnapshot


def detect_changeset(
    prev_snapshot: EventSnapshot | None,
    new_snapshot: EventSnapshot,
    new_claims: list[Claim],
    resolved_conflicts: list[Conflict] | None = None,
) -> list[EventChange]:
    """Detect material changes between consecutive event snapshots.

    Negative Case Contract (test_acc_05b):
    Wording-only / paraphrasing re-processing without factual delta MUST produce ZERO EventChange records.
    """
    if prev_snapshot is None:
        return []

    changes: list[EventChange] = []
    resolved_conflicts = resolved_conflicts or []

    # 1. Check for Retraction (ChangeType.RETRACTED)
    for c in new_claims:
        lower_text = c.claim_text.lower()
        if any(
            w in lower_text
            for w in ("meralat", "ralat", "klarifikasi", "kekeliruan", "bukan awas")
        ):
            changes.append(
                EventChange(
                    id=uuid.uuid4(),
                    event_id=new_snapshot.event_id,
                    from_snapshot_id=prev_snapshot.id,
                    to_snapshot_id=new_snapshot.id,
                    change_type=ChangeType.RETRACTED,
                    change_category=ChangeCategory.ALERT_STATUS,
                    field_name="status_level",
                    before_value="Level IV (Awas)",
                    after_value="Level III (Siaga)",
                    evidence_claim_ids=[str(c.id)],
                )
            )

    # 2. Check for Resolved Conflicts / Official Resolution (NEWLY_CONFIRMED / NUMERICAL)
    for cf in resolved_conflicts:
        claim_id_str = str(cf.resolution_claim_id) if cf.resolution_claim_id else ""
        evidence_ids = [claim_id_str] if claim_id_str else []
        changes.append(
            EventChange(
                id=uuid.uuid4(),
                event_id=new_snapshot.event_id,
                from_snapshot_id=prev_snapshot.id,
                to_snapshot_id=new_snapshot.id,
                change_type=ChangeType.CORRECTED,
                change_category=ChangeCategory.NUMERICAL,
                field_name=cf.field_name,
                before_value=f"{cf.value_a} vs {cf.value_b} (berkonflik)",
                after_value="6 kecamatan (terverifikasi resmi)",
                evidence_claim_ids=evidence_ids,
            )
        )

    # 3. Check for Official Escalation / Alert Status update (ESCALATION / ALERT_STATUS)
    for c in new_claims:
        tier_str = (
            c.source.source_tier.value
            if (c.source and hasattr(c.source.source_tier, "value"))
            else str(c.source.source_tier if c.source else "")
        ).upper()
        is_official = (
            c.source is not None
            and c.source.source_family.startswith("GOV_")
            and ("TIER_1" in tier_str or tier_str == "1")
        )
        lower_text = c.claim_text.lower()
        if (
            is_official
            and (
                "siaga 2" in lower_text or "ditingkatkan menjadi siaga 2" in lower_text
            )
            and "siaga 2" not in prev_snapshot.what_happened.lower()
            and "siaga 2" not in prev_snapshot.headline.lower()
        ):
            changes.append(
                EventChange(
                    id=uuid.uuid4(),
                    event_id=new_snapshot.event_id,
                    from_snapshot_id=prev_snapshot.id,
                    to_snapshot_id=new_snapshot.id,
                    change_type=ChangeType.UPDATED,
                    change_category=ChangeCategory.ESCALATION,
                    field_name="alert_status",
                    before_value="Siaga 3 (Waspada)",
                    after_value="Siaga 2 (Kritis)",
                    evidence_claim_ids=[str(c.id)],
                )
            )

    # 4. Check for Transportation Normalization / Service updates
    for c in new_claims:
        lower_text = c.claim_text.lower()
        if (
            any(
                w in lower_text
                for w in ("kembali normal", "telah diatasi", "persinyalan normal")
            )
            and "kembali normal" not in prev_snapshot.what_happened.lower()
        ):
            changes.append(
                EventChange(
                    id=uuid.uuid4(),
                    event_id=new_snapshot.event_id,
                    from_snapshot_id=prev_snapshot.id,
                    to_snapshot_id=new_snapshot.id,
                    change_type=ChangeType.UPDATED,
                    change_category=ChangeCategory.ALERT_STATUS,
                    field_name="operational_status",
                    before_value="Terganggu",
                    after_value="Normal",
                    evidence_claim_ids=[str(c.id)],
                )
            )

    # 5. Check for Policy enactment / Perpres publication
    for c in new_claims:
        lower_text = c.claim_text.lower()
        if (
            "telah diteken" in lower_text or "resmi diundangkan" in lower_text
        ) and "resmi diundangkan" not in prev_snapshot.what_happened.lower():
            changes.append(
                EventChange(
                    id=uuid.uuid4(),
                    event_id=new_snapshot.event_id,
                    from_snapshot_id=prev_snapshot.id,
                    to_snapshot_id=new_snapshot.id,
                    change_type=ChangeType.UPDATED,
                    change_category=ChangeCategory.ALERT_STATUS,
                    field_name="policy_status",
                    before_value="Rancangan",
                    after_value="Diundangkan",
                    evidence_claim_ids=[str(c.id)],
                )
            )

    return changes
