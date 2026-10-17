"""E2E test for API evidence citation accuracy.

Authority: DIM7-002, §53-C, DEC-0008, Addendum §5.2
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.staymad.api.dependencies import get_db
from backend.staymad.api.main import create_app
from backend.staymad.db.base import Base
from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.event import Event, EventSnapshot
from backend.staymad.db.session import create_session_factory
from backend.staymad.events.manager import EventSynthesisManager
from backend.staymad.ingest.pipeline import IngestExtractionPipeline
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.resolver.manager import EventResolverManager

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"


@pytest.fixture(scope="module")
def seeded_db():
    """Seed in-memory database with the 23-article demo fixture and return session factory."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    articles = data["articles"]

    llm = DeterministicGeminiClient()
    pipeline = IngestExtractionPipeline(llm_client=llm)

    with session_factory() as session:
        result = pipeline.process_batch(articles, session)
        run_id = result.processing_run_id

        resolver = EventResolverManager(
            session=session, llm_client=llm, ablation_mode="tier3"
        )
        for art_ver in result.article_versions:
            ver_claims = [
                c for c in result.claims if c.article_version_id == art_ver.id
            ]
            resolver.resolve_article_version(art_ver, ver_claims, run_id)
        session.commit()

        synth_mgr = EventSynthesisManager(session=session, llm_client=llm)
        all_events = session.scalars(select(Event)).all()
        for ev in all_events:
            synth_mgr.synthesize_event_snapshot(ev.id, run_id, force_snapshot=True)
        session.commit()

    return session_factory


@pytest.fixture
def client(seeded_db):
    """FastAPI TestClient with overridden database dependency."""
    app = create_app()

    def override_get_db():
        with seeded_db() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_returns_accurate_evidence_citations(client: TestClient, seeded_db):
    """Test that /events/{id} returns actual stored evidence_claim_ids."""
    with seeded_db() as session:
        events = session.scalars(select(Event)).all()
        target_event = next(
            ev
            for ev in events
            if any(
                "ciliwung" in (ec.claim.claim_text or "").lower()
                for ec in ev.event_claims
                if ec.claim
            )
        )
        event_id = target_event.id

    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200, response.text
    data = response.json()

    what_happened_ids = data["what_happened"]["evidence_claim_ids"]
    why_it_matters_ids = data["why_it_matters"]["evidence_claim_ids"]

    # Assert: Evidence arrays are DIFFERENT for different fields
    assert what_happened_ids != why_it_matters_ids, (
        "Evidence arrays should differ across narrative fields"
    )

    # Each array should contain only relevant claim IDs
    assert len(what_happened_ids) >= 1, "what_happened must have evidence"
    assert len(why_it_matters_ids) >= 1, "why_it_matters must have evidence"

    # Verify claim IDs exist in database
    with seeded_db() as session:
        for claim_id in what_happened_ids:
            claim_uuid = uuid.UUID(claim_id)
            assert session.get(Claim, claim_uuid) is not None, (
                f"Claim {claim_id} must exist in DB"
            )


def test_api_evidence_matches_snapshot_storage(client: TestClient, seeded_db):
    """Test that API evidence matches what's stored in EventSnapshot."""
    with seeded_db() as session:
        events = session.scalars(select(Event)).all()
        target_event = next(
            ev
            for ev in events
            if any(
                "ciliwung" in (ec.claim.claim_text or "").lower()
                for ec in ev.event_claims
                if ec.claim
            )
        )
        event_id = target_event.id

        snapshot = (
            session.query(EventSnapshot)
            .filter(EventSnapshot.event_id == event_id)
            .order_by(EventSnapshot.published_at.desc())
            .first()
        )
        assert snapshot is not None
        expected_what_happened = [
            str(x) for x in (snapshot.what_happened_evidence_claim_ids or [])
        ]
        expected_why_it_matters = [
            str(x) for x in (snapshot.why_it_matters_evidence_claim_ids or [])
        ]

    # Fetch from API
    api_response = client.get(f"/events/{event_id}").json()

    # Assert: API returns exactly what's stored
    assert api_response["what_happened"]["evidence_claim_ids"] == expected_what_happened
    assert (
        api_response["why_it_matters"]["evidence_claim_ids"] == expected_why_it_matters
    )
