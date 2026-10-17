"""Unit tests for Conflict Detection and Resolution.

Authority: docs/architecture/B-data-model.md §2.12, docs/architecture/E-timeline-algorithm.md §53-E Step 4,
Addendum §5, decisions.md Conflict #4
"""

from __future__ import annotations

import uuid

from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.enums import SourceTier, SourceType
from backend.staymad.db.models.source import Source
from backend.staymad.events.conflicts import ConflictDetector


def make_mock_claim_for_conflict(
    text: str,
    num_val: float | None = None,
    unit: str | None = None,
    source_family: str = "LKBN_ANTARA",
    source_tier: str = "TIER_1",
) -> Claim:
    c = Claim(
        id=uuid.uuid4(),
        article_version_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        claim_text=text,
        source_span=text[:40],
        numeric_value=num_val,
        unit=unit,
        extraction_confidence=0.9,
        language="id",
        model_version="mock",
        prompt_version="v1",
        schema_version="1.0",
        processing_run_id=uuid.uuid4(),
    )
    c.source = Source(
        id=c.source_id,
        name=source_family,
        url="https://news.example.com",
        source_type=SourceType.RSS,
        source_tier=SourceTier.TIER_1
        if source_tier in ("TIER_1", "1")
        else SourceTier.TIER_2,
        source_family=source_family,
    )
    return c


def test_detect_numerical_conflict():
    """Verify detection of conflicting numbers on the same metric (5 vs 7 kecamatan) per test_acc_04."""
    c1 = make_mock_claim_for_conflict(
        text="Hujan deras, banjir rendam 5 kecamatan di Jakarta Timur",
        num_val=5.0,
        unit="kecamatan",
        source_family="LKBN_ANTARA",
        source_tier="TIER_1",
    )
    c2 = make_mock_claim_for_conflict(
        text="Warga sebut 7 kecamatan di Jakarta Timur terendam luapan air",
        num_val=7.0,
        unit="kecamatan",
        source_family="MAHAKA_MEDIA",
        source_tier="TIER_2",
    )

    event_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    conflicts = ConflictDetector.detect_conflicts([c1, c2], event_id, snapshot_id)

    assert len(conflicts) == 1
    cf = conflicts[0]
    assert cf.field_name == "affected_kecamatan_count"
    assert cf.resolved is False
    assert (cf.value_a == "5" and cf.value_b == "7") or (
        cf.value_a == "7" and cf.value_b == "5"
    )
    assert cf.claim_a_id in (c1.id, c2.id)
    assert cf.claim_b_id in (c1.id, c2.id)


def test_resolve_numerical_conflict_via_official_update():
    """Verify that an official update claim resolves prior conflicting claims."""
    c1 = make_mock_claim_for_conflict(
        text="Banjir rendam 5 kecamatan",
        num_val=5.0,
        unit="kecamatan",
    )
    c2 = make_mock_claim_for_conflict(
        text="Banjir rendam 7 kecamatan",
        num_val=7.0,
        unit="kecamatan",
    )

    event_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    conflicts = ConflictDetector.detect_conflicts([c1, c2], event_id, snapshot_id)
    assert len(conflicts) == 1
    assert not conflicts[0].resolved

    # Official BPBD DKI update verifying 6 kecamatan
    c_official = make_mock_claim_for_conflict(
        text="Hasil verifikasi tim reaksi cepat di lapangan mencatat total 6 kecamatan terdampak genangan di Jakarta Timur",
        num_val=6.0,
        unit="kecamatan",
        source_family="GOV_BPBD_DKI",
        source_tier="TIER_1",
    )

    resolved = ConflictDetector.resolve_conflicts_with_update(
        conflicts, [c1, c2, c_official]
    )
    assert len(resolved) == 1
    assert resolved[0].resolved is True
    assert resolved[0].resolution_claim_id == c_official.id


def test_detect_status_conflict_and_clarification():
    """Verify detection of conflicting status (Level IV Awas vs Level III Siaga) and resolution via clarification."""
    c_initial = make_mock_claim_for_conflict(
        text="Laporan sempat menyebut status Merapi dinaikkan ke Level IV (Awas)",
        source_family="TRANSMEDIA",
        source_tier="TIER_2",
    )
    c_normal = make_mock_claim_for_conflict(
        text="Status aktivitas Gunung Merapi saat ini berada pada Level III (Siaga)",
        source_family="LKBN_ANTARA",
        source_tier="TIER_1",
    )

    event_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    conflicts = ConflictDetector.detect_conflicts(
        [c_initial, c_normal], event_id, snapshot_id
    )
    assert len(conflicts) == 1
    assert conflicts[0].field_name == "status_level"

    # Redaksi klarifikasi / ralat
    c_clarification = make_mock_claim_for_conflict(
        text="Redaksi meralat laporan sebelumnya: status tetap Level III, bukan Awas",
        source_family="TRANSMEDIA",
        source_tier="TIER_2",
    )

    resolved = ConflictDetector.resolve_conflicts_with_update(
        conflicts, [c_clarification]
    )
    assert resolved[0].resolved is True
    assert resolved[0].resolution_claim_id == c_clarification.id
