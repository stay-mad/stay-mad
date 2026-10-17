"""E2E test for accurate transparency metrics in /events/{id}/processing.

Authority: DIM1-001, DEC-0006
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.staymad.api.dependencies import get_db
from backend.staymad.api.main import create_app
from backend.staymad.db.base import Base
from backend.staymad.db.models.audit import EventMembershipAudit
from backend.staymad.db.models.event import Event
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


def test_processing_endpoint_accurate_counts(client: TestClient, seeded_db):
    """Test that /events/{id}/processing reports accurate candidate counts without inflation."""
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
        total_events = len(events)

        claims = [ec.claim for ec in target_event.event_claims if ec.claim is not None]
        art_ver_ids = {c.article_version_id for c in claims if c.article_version_id}
        audits = (
            session.scalars(
                select(EventMembershipAudit).where(
                    EventMembershipAudit.article_version_id.in_(art_ver_ids)
                )
            ).all()
            if art_ver_ids
            else []
        )
        candidate_ids = set()
        for aud in audits:
            if aud.candidate_event_ids:
                candidate_ids.update(aud.candidate_event_ids)
        expected_candidates = len(candidate_ids)

    response = client.get(f"/events/{event_id}/processing")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["candidate_events_considered"] == expected_candidates, (
        f"Expected {expected_candidates} candidates, got {data['candidate_events_considered']}"
    )

    # Transparency check: Should NOT equal total database events if evaluated candidates was smaller
    if expected_candidates < total_events:
        assert data["candidate_events_considered"] < total_events, (
            "Candidate count should not inflate to total DB size"
        )
