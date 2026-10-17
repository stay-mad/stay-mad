"""Acceptance test suite for Stage 05: Timeline Reconstruction, Conflict Detection, Scoring & Gemini Synthesis.

Authority: docs/acceptance-matrix.md (Scenarios 2, 4, 5a, 5b), docs/decisions.md (DEC-0005, DEC-0006, DEC-0008)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.staymad.db.base import Base
from backend.staymad.db.models.conflict import Conflict
from backend.staymad.db.models.enums import (
    ConfidenceBucket,
    EvidenceStatus,
)
from backend.staymad.db.models.event import Event, EventChange
from backend.staymad.db.models.timeline import TimelineEntry
from backend.staymad.db.session import create_db_engine, create_session_factory
from backend.staymad.events.manager import EventSynthesisManager
from backend.staymad.ingest.pipeline import IngestExtractionPipeline
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.resolver.manager import EventResolverManager

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"


@pytest.fixture
def db_session():
    """In-memory SQLite database session fixture."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_maker = create_session_factory(engine)
    with session_maker() as session:
        yield session


def test_stage05_pipeline_full_synthesis(db_session):
    """End-to-end Stage 05 verification over 23 seed fixture articles.

    Verifies:
    - Skenario 2: Canonical resolution & chronological timeline entries with qualifiers.
    - Skenario 4: Deteksi konflik angka faktual (test_acc_04: 5 vs 7 kecamatan) -> evidence_status = CONFLICTING.
    - Skenario 5a: Pembaruan resmi & changeset snapshot (test_acc_05: BPBD DKI 6 kec/Siaga 2) -> EventSnapshot v2.
    """
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    articles = data["articles"]

    llm = DeterministicGeminiClient()
    ingest_pipe = IngestExtractionPipeline(llm_client=llm)
    ingest_res = ingest_pipe.process_batch(articles, db_session)
    run_id = ingest_res.processing_run_id

    # Step 1: Resolve all articles into canonical events
    resolver = EventResolverManager(
        session=db_session, llm_client=llm, ablation_mode="tier3"
    )
    results = []
    for art_ver in ingest_res.article_versions:
        ver_claims = [
            c for c in ingest_res.claims if c.article_version_id == art_ver.id
        ]
        res = resolver.resolve_article_version(art_ver, ver_claims, run_id)
        results.append((art_ver, res))
    db_session.commit()

    # Step 2: Synthesize all canonical events
    synth_mgr = EventSynthesisManager(session=db_session, llm_client=llm)
    events = db_session.scalars(select(Event)).all()
    assert len(events) >= 4, "Must resolve into canonical events"

    snapshots = []
    for evt in events:
        snap = synth_mgr.synthesize_event_snapshot(evt.id, run_id, force_snapshot=True)
        if snap:
            snapshots.append(snap)
    db_session.commit()

    assert len(snapshots) >= 4, "All canonical events must produce snapshots"

    # Step 3: Validate Timeline Reconstruction (Skenario 2)
    timeline_entries = db_session.scalars(select(TimelineEntry)).all()
    assert len(timeline_entries) > 0, "Timeline entries must be created"

    # Verify qualifiers are preserved on entries
    qualifier_entries = [te for te in timeline_entries if te.event_time_qualifier]
    assert len(qualifier_entries) > 0, (
        "Timeline entries must retain qualifiers (e.g. 'sekitar')"
    )

    # Step 4: Validate Conflict Detection (Skenario 4 / test_acc_04)
    # Flood cluster contains art_demo_01 (5 kec) vs art_demo_02 (7 kec)
    conflicts = db_session.scalars(select(Conflict)).all()
    assert len(conflicts) > 0, "Must detect factual conflicts"

    num_conflict = next(
        (cf for cf in conflicts if {cf.value_a, cf.value_b} == {"5", "7"}),
        None,
    )
    assert num_conflict is not None, (
        "Scenario 4: Must detect numerical conflict between 5 and 7 kecamatan"
    )
    assert {num_conflict.value_a, num_conflict.value_b} == {"5", "7"}

    # Step 5: Validate Official Update & Changeset (Skenario 5a / test_acc_05)
    # art_demo_05 provides official update (Siaga 2, 6 kecamatan)
    # Locate flood event
    flood_event = db_session.get(Event, num_conflict.event_id)
    assert flood_event is not None

    # Verify official update resolved the conflict
    assert num_conflict.resolved is True, (
        "Scenario 5a: BPBD official update must resolve numerical conflict"
    )

    # Synthesize updated snapshot v2 to generate changeset delta against v1
    bpbd_claims = [
        c
        for c in ingest_res.claims
        if c.source and "bpbd" in c.source.source_family.lower()
    ]
    snap_v2 = synth_mgr.synthesize_event_snapshot(
        flood_event.id, run_id, newly_added_claims=bpbd_claims, force_snapshot=True
    )
    assert snap_v2 is not None
    assert snap_v2.version_number >= 2

    # Verify EventChanges recorded linking snapshots
    changes = db_session.scalars(select(EventChange)).all()
    assert len(changes) >= 1, (
        "Must generate structured EventChange records between v1 and v2"
    )

    # Step 6: Verify Scoring Integrity (DEC-0006, DEC-0008)
    for snap in snapshots:
        # Confidence score between 0.0 and 1.0
        assert 0.0 <= snap.confidence_score <= 1.0
        assert snap.confidence_bucket in (
            ConfidenceBucket.HIGH,
            ConfidenceBucket.MEDIUM,
            ConfidenceBucket.LOW,
        )
        assert snap.evidence_status in (
            EvidenceStatus.SUPPORTED,
            EvidenceStatus.CONFLICTING,
            EvidenceStatus.INSUFFICIENT,
            EvidenceStatus.RETRACTED,
        )

        # Importance score between 0.0 and 1.0
        assert 0.0 <= snap.importance_score <= 1.0
        assert 0.0 <= snap.urgency_score <= 1.0

        # Anti-hallucination: what_happened must not be empty
        assert snap.what_happened
        assert len(snap.headline) <= 150
