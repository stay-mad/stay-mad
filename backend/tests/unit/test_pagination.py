"""Unit tests for Server-Side Pagination, Search Query (q), and Aggregate Stats (Item A2).

Authority: docs/UI_REFACTOR_V2.md §A2, docs/contracts/openapi.yaml
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.staymad.api.dependencies import get_db
from backend.staymad.api.main import create_app
from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import (
    ActionabilityLevel,
    ConfidenceBucket,
    DataMode,
    EventCategory,
    EvidenceStatus,
    VerificationLevel,
)
from backend.staymad.db.models.event import Event, EventSnapshot


@pytest.fixture
def paged_test_db_session():
    """Seed in-memory database with 25 distinct events for pagination testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        events = []
        snapshots = []
        for i in range(25):
            ev = Event(
                id=uuid.uuid4(),
                event_type="DISASTER" if i % 2 == 0 else "TRANSPORT",
                category=(
                    EventCategory.DISASTER_AND_WEATHER
                    if i % 2 == 0
                    else EventCategory.TRANSPORTATION_AND_INFRASTRUCTURE
                ),
                primary_location_id=None,
                time_window_start=datetime.now(UTC),
                time_window_end=datetime.now(UTC),
            )
            # High urgency for first 5 events
            is_urgent = i < 5
            # Official primary for first 10 events
            is_official = i < 10
            # Conflicting for last 3 events
            is_conflicting = i >= 22

            snap = EventSnapshot(
                id=uuid.uuid4(),
                event_id=ev.id,
                version_number=1,
                published_at=datetime.now(UTC),
                headline=f"Peristiwa Berita Penting #{i + 1:02d} Gempa dan Cuaca Ekstrem"
                if i % 3 == 0
                else f"Peristiwa Transportasi Kereta Api #{i + 1:02d}",
                what_happened=f"Rincian peristiwa #{i + 1}.",
                confidence_score=0.8,
                confidence_bucket=ConfidenceBucket.HIGH,
                evidence_status=(
                    EvidenceStatus.CONFLICTING
                    if is_conflicting
                    else EvidenceStatus.SUPPORTED
                ),
                verification_level=(
                    VerificationLevel.OFFICIAL_PRIMARY
                    if is_official
                    else VerificationLevel.SINGLE_SOURCE
                ),
                actionability_level=(
                    ActionabilityLevel.ACTION_REQUIRED
                    if is_urgent
                    else ActionabilityLevel.INFORMATIONAL
                ),
                importance_score=0.90 if is_urgent else 0.50,
                urgency_score=0.85 if is_urgent else 0.4,
                data_mode=DataMode.LIVE,
                last_processed_at=datetime.now(UTC),
                model_version="gemini-2.0-flash",
                prompt_version="v1.0",
                schema_version="1.0.0",
                processing_run_id=uuid.uuid4(),
            )
            events.append(ev)
            snapshots.append(snap)

        session.add_all(events)
        session.flush()
        session.add_all(snapshots)
        session.commit()

        yield session


@pytest.fixture
def client(paged_test_db_session: Session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: paged_test_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_default_pagination_limit_twelve(client: TestClient):
    """Default limit is 12 per requirements A2.1."""
    resp = client.get("/events?data_mode=live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert data["limit"] == 12
    assert data["offset"] == 0
    assert len(data["events"]) == 12


def test_page_navigation_offset(client: TestClient):
    """Test first page, middle page, and final page offsets."""
    # Page 1: 0..11
    resp_p1 = client.get("/events?data_mode=live&offset=0&limit=12")
    data_p1 = resp_p1.json()
    assert len(data_p1["events"]) == 12
    first_id = data_p1["events"][0]["id"]

    # Page 2: 12..23
    resp_p2 = client.get("/events?data_mode=live&offset=12&limit=12")
    data_p2 = resp_p2.json()
    assert len(data_p2["events"]) == 12
    assert data_p2["events"][0]["id"] != first_id

    # Page 3: 24..24 (only 1 remaining out of 25)
    resp_p3 = client.get("/events?data_mode=live&offset=24&limit=12")
    data_p3 = resp_p3.json()
    assert len(data_p3["events"]) == 1
    assert data_p3["total"] == 25


def test_offset_beyond_total(client: TestClient):
    """Offset greater than total items returns empty list, not error."""
    resp = client.get("/events?data_mode=live&offset=100&limit=12")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total"] == 25


def test_server_side_headline_search_q(client: TestClient):
    """Search query 'q' filters headlines across entire database before pagination."""
    resp = client.get("/events?data_mode=live&q=Gempa")
    assert resp.status_code == 200
    data = resp.json()
    # Headlines with Gempa: indices 0, 3, 6, 9, 12, 15, 18, 21, 24 -> 9 items
    assert data["total"] == 9
    for ev in data["events"]:
        assert "Gempa" in ev["headline"]


def test_summary_stats_reflects_overall_total_not_page_slice(client: TestClient):
    """Summary stats in response must reflect overall matched filter count, not 12 on current page."""
    resp = client.get("/events?data_mode=live&offset=0&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 5
    assert data["total"] == 25

    stats = data["summary_stats"]
    assert stats is not None
    assert stats["total"] == 25
    assert stats["need_to_know"] == 5
    assert stats["official_primary"] == 10
    assert stats["conflicts"] == 3


def test_backward_compatibility_custom_limit(client: TestClient):
    """Legacy clients requesting limit=20 or other values still work unchanged."""
    resp = client.get("/events?data_mode=live&limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 20
    assert data["limit"] == 20
