"""Unit tests for Confidence Scoring and Importance Scoring Algorithms.

Authority: docs/architecture/F-confidence-algorithm.md (§53-F),
docs/architecture/G-importance-algorithm.md (§53-G), decisions.md Conflict #1, #3
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.staymad.confidence.calculator import calculate_confidence
from backend.staymad.confidence.config import ConfidenceConfig
from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.conflict import Conflict
from backend.staymad.db.models.enums import (
    ActionabilityLevel,
    ConfidenceBucket,
    EventCategory,
    EvidenceStatus,
    SourceTier,
    SourceType,
    TimelinePrecision,
    VerificationLevel,
)
from backend.staymad.db.models.event import Event
from backend.staymad.db.models.location import Location
from backend.staymad.db.models.source import Source
from backend.staymad.intelligence.calculator import calculate_importance
from backend.staymad.intelligence.config import ImportanceConfig


def make_test_claim(
    text: str,
    source_family: str = "LKBN_ANTARA",
    source_tier: str = "TIER_1",
    event_time: datetime | None = None,
    event_time_raw: str | None = None,
) -> Claim:
    c = Claim(
        id=uuid.uuid4(),
        article_version_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        claim_text=text,
        source_span=text[:30],
        event_time=event_time,
        event_time_raw=event_time_raw or ("08:00 WIB" if event_time else None),
        event_time_precision=TimelinePrecision.EXACT
        if event_time
        else TimelinePrecision.UNKNOWN,
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
        url="https://example.com/feed",
        source_type=SourceType.RSS,
        source_tier=SourceTier.TIER_1
        if source_tier in ("TIER_1", "1")
        else SourceTier.TIER_2,
        source_family=source_family,
    )
    return c


def test_confidence_formula_and_mapping():
    """Verify 5-component confidence formula and mapping to buckets and status."""
    cfg = ConfidenceConfig.load()

    t = datetime(2026, 10, 10, 1, 0, tzinfo=UTC)
    c1 = make_test_claim(
        text="BPBD DKI catat banjir di 6 kecamatan",
        source_family="GOV_BPBD_DKI",
        source_tier="TIER_1",
        event_time=t,
    )
    c2 = make_test_claim(
        text="ANTARA laporkan air genangi jalan",
        source_family="LKBN_ANTARA",
        source_tier="TIER_1",
        event_time=t,
    )

    res = calculate_confidence([c1, c2], conflicts=[], config=cfg)

    # 1. source_quality: GOV_BPBD_DKI TIER_1 -> 1.0
    assert res.components["source_quality"] == 1.0
    # 2. corroboration: 2 unique families / 4 max = 0.50
    assert res.components["corroboration"] == 0.50
    # 3. claim_consistency: 0 conflicts -> 1.0
    assert res.components["claim_consistency"] == 1.0
    # 4. official_confirmation: has GOV_* -> 1.0
    assert res.components["official_confirmation"] == 1.0
    # 5. temporal_consistency: all resolved -> 1.0
    assert res.components["temporal_consistency"] == 1.0

    # Expected: 0.30*1.0 + 0.25*0.5 + 0.20*1.0 + 0.15*1.0 + 0.10*1.0 = 0.30 + 0.125 + 0.20 + 0.15 + 0.10 = 0.875
    assert res.confidence_score == 0.875
    assert res.confidence_bucket == ConfidenceBucket.HIGH
    assert res.evidence_status == EvidenceStatus.SUPPORTED
    assert res.verification_level == VerificationLevel.OFFICIAL_PRIMARY


def test_confidence_conflicting_unresolved_status():
    """Verify that unresolved conflicts reduce claim_consistency and set evidence_status = CONFLICTING."""
    c1 = make_test_claim(
        "5 kecamatan terendam", source_family="LKBN_ANTARA", source_tier="TIER_1"
    )
    c2 = make_test_claim(
        "7 kecamatan terendam", source_family="MAHAKA_MEDIA", source_tier="TIER_2"
    )

    cf = Conflict(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        field_name="affected_kecamatan_count",
        claim_a_id=c1.id,
        claim_b_id=c2.id,
        value_a="5",
        value_b="7",
        resolved=False,
    )

    res = calculate_confidence([c1, c2], conflicts=[cf])
    assert res.evidence_status == EvidenceStatus.CONFLICTING
    assert res.components["claim_consistency"] < 1.0


def test_importance_excludes_confidence_score():
    """Verify Conflict #1 resolution: confidence is strictly NOT in the importance score calculation."""
    cfg = ImportanceConfig.load()
    evt = Event(
        id=uuid.uuid4(),
        event_type="Banjir Luapan Ciliwung",
        category=EventCategory.DISASTER_AND_WEATHER,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    evt.primary_location = Location(
        id=uuid.uuid4(),
        city="Jakarta Timur",
        province="DKI Jakarta",
        country="Indonesia",
    )

    claims = [
        make_test_claim(
            "BPBD DKI tingkatkan status Siaga 2 banjir rendam permukiman di Jakarta Timur",
            "GOV_BPBD_DKI",
            "TIER_1",
        ),
        make_test_claim("Ketinggian air naik di Cipinang", "LKBN_ANTARA", "TIER_1"),
    ]

    res = calculate_importance(
        event=evt,
        claims=claims,
        actionability_level=ActionabilityLevel.ACTION_REQUIRED,
        config=cfg,
    )

    # Importance weights sum to 1.0 across the 5 independent factors
    assert "confidence" not in res.components
    assert res.importance_score > 0.60
    assert res.urgency_score > 0.60
    # High impact and high urgency triggers NEED TO KNOW per §53-G §4
    assert res.ui_label in ("NEED TO KNOW", "ACTION REQUIRED")
