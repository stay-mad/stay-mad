"""Unit tests for Event Changeset and Negative Wording-Only Reprocessing.

Authority: Addendum §7, Addendum §11 Skenario 5a & 5b (test_acc_05 & test_acc_05b), DEC-0005
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.conflict import Conflict
from backend.staymad.db.models.enums import (
    ActionabilityLevel,
    ChangeCategory,
    ChangeType,
    ConfidenceBucket,
    EvidenceStatus,
    SourceTier,
    SourceType,
    VerificationLevel,
)
from backend.staymad.db.models.event import EventSnapshot
from backend.staymad.db.models.source import Source
from backend.staymad.events.changes import detect_changeset


def make_snapshot(headline: str, what_happened: str, version: int = 1) -> EventSnapshot:
    return EventSnapshot(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        version_number=version,
        published_at=datetime.now(UTC),
        headline=headline,
        what_happened=what_happened,
        confidence_score=0.8,
        confidence_bucket=ConfidenceBucket.HIGH,
        evidence_status=EvidenceStatus.SUPPORTED,
        verification_level=VerificationLevel.OFFICIAL_PRIMARY,
        actionability_level=ActionabilityLevel.INFORMATIONAL,
        importance_score=0.75,
        urgency_score=0.6,
        model_version="mock",
        prompt_version="v1",
        schema_version="1.0",
        processing_run_id=uuid.uuid4(),
    )


def test_acc_05_official_update_changeset():
    """Verify Scenario 5a: Official update generates structured EventChange records."""
    prev_snap = make_snapshot(
        headline="Banjir Rendam Sejumlah Titik di Jakarta Timur",
        what_happened="Genangan banjir dilaporkan melanda sejumlah kecamatan di Jakarta Timur dengan ketinggian bervariasi.",
        version=1,
    )
    new_snap = make_snapshot(
        headline="Peringatan Dini BPBD: Banjir Jakarta Timur Siaga 2, Terverifikasi 6 Kecamatan",
        what_happened="BPBD DKI Jakarta mengonfirmasi kenaikan status Siaga 2 dan 6 kecamatan terverifikasi terdampak.",
        version=2,
    )

    c_official = Claim(
        id=uuid.uuid4(),
        article_version_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        claim_text="Status penanganan ditingkatkan menjadi Siaga 2 menyusul kenaikan debit air. Total 6 kecamatan terdampak genangan.",
        source_span="ditingkatkan menjadi Siaga 2",
        extraction_confidence=0.95,
        language="id",
        model_version="mock",
        prompt_version="v1",
        schema_version="1.0",
        processing_run_id=uuid.uuid4(),
    )
    c_official.source = Source(
        id=c_official.source_id,
        name="BPBD DKI",
        url="https://bpbd.jakarta.go.id",
        source_type=SourceType.OFFICIAL_GOV,
        source_tier=SourceTier.TIER_1,
        source_family="GOV_BPBD_DKI",
    )

    cf_resolved = Conflict(
        id=uuid.uuid4(),
        event_id=new_snap.event_id,
        snapshot_id=prev_snap.id,
        field_name="affected_kecamatan_count",
        claim_a_id=uuid.uuid4(),
        claim_b_id=uuid.uuid4(),
        value_a="5",
        value_b="7",
        resolved=True,
        resolution_claim_id=c_official.id,
    )

    changes = detect_changeset(
        prev_snapshot=prev_snap,
        new_snapshot=new_snap,
        new_claims=[c_official],
        resolved_conflicts=[cf_resolved],
    )

    assert len(changes) >= 2

    # Check numerical conflict resolution change
    num_changes = [c for c in changes if c.change_category == ChangeCategory.NUMERICAL]
    assert len(num_changes) == 1
    assert num_changes[0].change_type == ChangeType.CORRECTED
    assert num_changes[0].field_name == "affected_kecamatan_count"

    # Check alert status escalation change
    status_changes = [
        c for c in changes if c.change_category == ChangeCategory.ESCALATION
    ]
    assert len(status_changes) == 1
    assert status_changes[0].change_type == ChangeType.UPDATED
    assert status_changes[0].field_name == "alert_status"


def test_acc_05b_no_changeset_wording_only():
    """Verify Scenario 5b (Negative Case): Reprocessing with wording-only variation produces ZERO EventChange records.

    Authority: Addendum §7 L110, §11 (5), no-change specificity = 1.00.
    """
    prev_snap = make_snapshot(
        headline="Banjir Rendam 5 Kecamatan di Jakarta Timur",
        what_happened="Hujan deras menyebabkan luapan Kali Ciliwung merendam lima kecamatan di Jakarta Timur.",
        version=1,
    )
    new_snap = make_snapshot(
        headline="Genangan Banjir Landa Lima Kawasan Jakarta Timur",
        what_happened="Luapan air Sungai Ciliwung akibat hujan deras menggenangi 5 kecamatan di Jakarta Timur.",
        version=2,
    )

    # Paraphrased/syndicated claims with no new numbers, no official status changes, no retractions
    c_syndicated = Claim(
        id=uuid.uuid4(),
        article_version_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        claim_text="Sejumlah kawasan di Jakarta Timur terendam banjir akibat luapan aliran Kali Ciliwung pada Sabtu pagi.",
        source_span="kawasan Jakarta Timur terendam banjir",
        extraction_confidence=0.9,
        language="id",
        model_version="mock",
        prompt_version="v1",
        schema_version="1.0",
        processing_run_id=uuid.uuid4(),
    )
    c_syndicated.source = Source(
        id=c_syndicated.source_id,
        name="CNN Indonesia",
        url="https://cnnindonesia.com",
        source_type=SourceType.RSS,
        source_tier=SourceTier.TIER_2,
        source_family="TRANSMEDIA",
    )

    changes = detect_changeset(
        prev_snapshot=prev_snap,
        new_snapshot=new_snap,
        new_claims=[c_syndicated],
        resolved_conflicts=[],
    )

    # ZERO changes detected for wording-only reprocessing
    assert len(changes) == 0, (
        f"Expected 0 changes for wording-only variation, got {len(changes)}"
    )
