"""Unit tests for Timeline Reconstruction, Temporal Sorting, and Qualifier Preservation.

Authority: docs/architecture/E-timeline-algorithm.md (§53-E), DEC-0001
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.staymad.db.models.article import ArticleVersion
from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.enums import (
    SourceTier,
    SourceType,
    TimelinePrecision,
)
from backend.staymad.db.models.source import Source
from backend.staymad.timeline.builder import (
    build_timeline_entries,
    deduplicate_temporal_claims,
    format_timeline_display_time,
)


def make_mock_claim(
    text: str,
    event_time: datetime | None = None,
    precision: TimelinePrecision = TimelinePrecision.EXACT,
    qualifier: str | None = None,
    published_time: datetime | None = None,
    source_family: str = "LKBN_ANTARA",
    source_tier: str = "TIER_1",
) -> Claim:
    """Helper to construct Claim with associated ArticleVersion and Source."""
    c = Claim(
        id=uuid.uuid4(),
        article_version_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        claim_text=text,
        source_span=text[:50],
        event_time=event_time,
        event_time_precision=precision,
        event_time_qualifier=qualifier,
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
        url="https://example.com/rss",
        source_type=SourceType.RSS,
        source_tier=SourceTier.TIER_1
        if source_tier in ("TIER_1", "1")
        else SourceTier.TIER_2,
        source_family=source_family,
    )
    c.article_version = ArticleVersion(
        id=c.article_version_id,
        article_id=uuid.uuid4(),
        title="Sample",
        excerpt=text[:200],
        content_hash="abc",
        published_time=published_time or datetime(2026, 10, 10, 8, 0, tzinfo=UTC),
    )
    return c


def test_timeline_chronological_ordering():
    """Verify known_time is sorted chronologically and unknown_time is ordered by published_time."""
    c1 = make_mock_claim(
        text="Air mulai menggenangi permukiman warga",
        event_time=datetime(2026, 10, 10, 1, 0, tzinfo=UTC),  # 08:00 WIB
        published_time=datetime(2026, 10, 10, 1, 30, tzinfo=UTC),
    )
    c2 = make_mock_claim(
        text="Ketinggian air naik mencapai 80 sentimeter",
        event_time=datetime(2026, 10, 10, 2, 30, tzinfo=UTC),  # 09:30 WIB
        published_time=datetime(2026, 10, 10, 2, 45, tzinfo=UTC),
    )
    c3 = make_mock_claim(
        text="Hujan deras dilaporkan mengguyur sejak subuh",
        event_time=datetime(2026, 10, 9, 23, 0, tzinfo=UTC),  # 06:00 WIB
        published_time=datetime(2026, 10, 10, 1, 0, tzinfo=UTC),
    )
    c_unknown = make_mock_claim(
        text="Warga memindahkan barang ke lantai dua rumah",
        event_time=None,
        precision=TimelinePrecision.UNKNOWN,
        published_time=datetime(2026, 10, 10, 3, 0, tzinfo=UTC),
    )

    event_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    entries = build_timeline_entries([c1, c2, c3, c_unknown], event_id, snapshot_id)

    assert len(entries) == 4
    # Chronological: 06:00 (c3) -> 08:00 (c1) -> 09:30 (c2) -> unknown (c_unknown)
    assert entries[0].description == c3.claim_text
    assert entries[0].order_index == 0
    assert entries[1].description == c1.claim_text
    assert entries[1].order_index == 1
    assert entries[2].description == c2.claim_text
    assert entries[2].order_index == 2
    assert entries[3].description == c_unknown.claim_text
    assert entries[3].order_index == 3


def test_timeline_qualifier_preservation():
    """Verify temporal qualifiers ('sekitar', 'diperkirakan') are retained in TimelineEntry and display."""
    c = make_mock_claim(
        text="Luapan air mulai masuk permukiman sekitar pukul 08:30 WIB",
        event_time=datetime(2026, 10, 10, 1, 30, tzinfo=UTC),  # 08:30 WIB
        precision=TimelinePrecision.APPROXIMATE,
        qualifier="sekitar",
    )

    entries = build_timeline_entries([c], uuid.uuid4(), uuid.uuid4())
    assert len(entries) == 1
    entry = entries[0]
    assert entry.event_time_precision == TimelinePrecision.APPROXIMATE
    assert entry.event_time_qualifier == "sekitar"

    # Display formatting must keep qualifier per §53-E §4
    display_str = format_timeline_display_time(
        entry.event_time,
        entry.event_time_precision,
        entry.event_time_qualifier,
    )
    assert "Sekitar" in display_str
    assert "08:30 WIB" in display_str


def test_temporal_deduplication_same_family_and_time():
    """Verify claims from the same source_family with the same event_time are deduplicated per §53-E Step 3."""
    t = datetime(2026, 10, 10, 1, 0, tzinfo=UTC)
    c_detik = make_mock_claim(
        text="Laporan pertama detik",
        event_time=t,
        source_family="TRANSMEDIA",
    )
    c_cnn = make_mock_claim(
        text="Laporan kedua CNN (sindikasi TRANSMEDIA)",
        event_time=t,
        source_family="TRANSMEDIA",
    )
    c_antara = make_mock_claim(
        text="Laporan ANTARA independen",
        event_time=t,
        source_family="LKBN_ANTARA",
    )

    deduped = deduplicate_temporal_claims([c_detik, c_cnn, c_antara])
    # c_detik and c_cnn share TRANSMEDIA family + identical event_time -> 1 entry
    # c_antara is LKBN_ANTARA -> kept
    assert len(deduped) == 2
    families = {c.source.source_family for c in deduped}
    assert families == {"TRANSMEDIA", "LKBN_ANTARA"}


def test_format_timeline_display_rules():
    """Verify all 5 precision display rules from §53-E §4 and DEC-0001."""
    t = datetime(2026, 10, 10, 1, 15, tzinfo=UTC)  # 08:15 WIB

    # 1. EXACT
    assert format_timeline_display_time(t, TimelinePrecision.EXACT) == "08:15 WIB"

    # 2. APPROXIMATE
    assert (
        format_timeline_display_time(t, TimelinePrecision.APPROXIMATE, "sekitar")
        == "Sekitar 08:15 WIB"
    )

    # 3. DAY
    assert format_timeline_display_time(t, TimelinePrecision.DAY) == "10 Oktober 2026"

    # 4. RANGE
    assert format_timeline_display_time(t, TimelinePrecision.RANGE) == "08:15 WIB"

    # 5. UNKNOWN with published_time
    pub_t = datetime(2026, 10, 10, 7, 0, tzinfo=UTC)  # 14:00 WIB
    assert "dilaporkan ~14:00 WIB" in format_timeline_display_time(
        None, TimelinePrecision.UNKNOWN, published_time=pub_t
    )
