"""Unit tests for Location Filtering and Hierarchy (Item A1).

Authority: docs/UI_REFACTOR_V2.md §A1, docs/contracts/openapi.yaml
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
    GeoLevel,
    VerificationLevel,
)
from backend.staymad.db.models.event import Event, EventSnapshot
from backend.staymad.db.models.location import Location


@pytest.fixture
def test_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Create test locations
        loc_jaktim = Location(
            id=uuid.uuid4(),
            city="Jakarta Timur",
            province="DKI Jakarta",
            country="Indonesia",
            geo_level=GeoLevel.CITY,
            canonical_name="Jakarta Timur",
            source_text="Jakarta Timur, DKI Jakarta",
        )
        loc_jakbar = Location(
            id=uuid.uuid4(),
            city="Jakarta Barat",
            province="DKI Jakarta",
            country="Indonesia",
            geo_level=GeoLevel.CITY,
            canonical_name="Jakarta Barat",
            source_text="Jakarta Barat, DKI Jakarta",
        )
        loc_jogja = Location(
            id=uuid.uuid4(),
            city="Kawasan Merapi",
            province="DI Yogyakarta",
            country="Indonesia",
            geo_level=GeoLevel.CITY,
            canonical_name="Kawasan Merapi",
            source_text="Kawasan Merapi, DI Yogyakarta",
        )
        session.add_all([loc_jaktim, loc_jakbar, loc_jogja])
        session.flush()

        # Create Events
        # 1. Event in Jakarta Timur (DKI Jakarta)
        ev1 = Event(
            id=uuid.uuid4(),
            event_type="FLOOD",
            category=EventCategory.DISASTER_AND_WEATHER,
            primary_location_id=loc_jaktim.id,
            time_window_start=datetime.now(UTC),
            time_window_end=datetime.now(UTC),
        )
        snap1 = EventSnapshot(
            id=uuid.uuid4(),
            event_id=ev1.id,
            version_number=1,
            published_at=datetime.now(UTC),
            headline="Banjir luapan Kali Ciliwung merendam Kampung Melayu Jakarta Timur",
            what_happened="Banjir melanda wilayah Jakarta Timur.",
            confidence_score=0.85,
            confidence_bucket=ConfidenceBucket.HIGH,
            evidence_status=EvidenceStatus.SUPPORTED,
            verification_level=VerificationLevel.OFFICIAL_PRIMARY,
            actionability_level=ActionabilityLevel.ACTION_REQUIRED,
            importance_score=0.9,
            urgency_score=0.85,
            data_mode=DataMode.LIVE,
            last_processed_at=datetime.now(UTC),
            model_version="gemini-2.0-flash",
            prompt_version="v1.0",
            schema_version="1.0.0",
            processing_run_id=uuid.uuid4(),
        )

        # 2. Event in Jakarta Barat (DKI Jakarta)
        ev2 = Event(
            id=uuid.uuid4(),
            event_type="ROB_FLOOD",
            category=EventCategory.DISASTER_AND_WEATHER,
            primary_location_id=loc_jakbar.id,
            time_window_start=datetime.now(UTC),
            time_window_end=datetime.now(UTC),
        )
        snap2 = EventSnapshot(
            id=uuid.uuid4(),
            event_id=ev2.id,
            version_number=1,
            published_at=datetime.now(UTC),
            headline="Banjir rob genangi pemukiman Muara Angke Jakarta Barat",
            what_happened="Rob pasang laut di Jakarta Barat.",
            confidence_score=0.8,
            confidence_bucket=ConfidenceBucket.HIGH,
            evidence_status=EvidenceStatus.SUPPORTED,
            verification_level=VerificationLevel.INDEPENDENTLY_CORROBORATED,
            actionability_level=ActionabilityLevel.INFORMATIONAL,
            importance_score=0.7,
            urgency_score=0.6,
            data_mode=DataMode.LIVE,
            last_processed_at=datetime.now(UTC),
            model_version="gemini-2.0-flash",
            prompt_version="v1.0",
            schema_version="1.0.0",
            processing_run_id=uuid.uuid4(),
        )

        # 3. Event in DI Yogyakarta
        ev3 = Event(
            id=uuid.uuid4(),
            event_type="VOLCANO",
            category=EventCategory.DISASTER_AND_WEATHER,
            primary_location_id=loc_jogja.id,
            time_window_start=datetime.now(UTC),
            time_window_end=datetime.now(UTC),
        )
        snap3 = EventSnapshot(
            id=uuid.uuid4(),
            event_id=ev3.id,
            version_number=1,
            published_at=datetime.now(UTC),
            headline="Aktivitas vulkanik Gunung Merapi Yogyakarta meningkat",
            what_happened="Erupsi Merapi di Yogyakarta.",
            confidence_score=0.9,
            confidence_bucket=ConfidenceBucket.HIGH,
            evidence_status=EvidenceStatus.SUPPORTED,
            verification_level=VerificationLevel.OFFICIAL_PRIMARY,
            actionability_level=ActionabilityLevel.ACTION_REQUIRED,
            importance_score=0.95,
            urgency_score=0.9,
            data_mode=DataMode.LIVE,
            last_processed_at=datetime.now(UTC),
            model_version="gemini-2.0-flash",
            prompt_version="v1.0",
            schema_version="1.0.0",
            processing_run_id=uuid.uuid4(),
        )

        # 4. National Event (No primary location, country=Indonesia)
        ev4 = Event(
            id=uuid.uuid4(),
            event_type="POLICY",
            category=EventCategory.GOVERNMENT_AND_PUBLIC_POLICY,
            primary_location_id=None,
            time_window_start=datetime.now(UTC),
            time_window_end=datetime.now(UTC),
        )
        snap4 = EventSnapshot(
            id=uuid.uuid4(),
            event_id=ev4.id,
            version_number=1,
            published_at=datetime.now(UTC),
            headline="Presiden RI mengumumkan paket stimulus ekonomi nasional",
            what_happened="Kebijakan ekonomi berskala nasional.",
            confidence_score=0.9,
            confidence_bucket=ConfidenceBucket.HIGH,
            evidence_status=EvidenceStatus.SUPPORTED,
            verification_level=VerificationLevel.OFFICIAL_PRIMARY,
            actionability_level=ActionabilityLevel.INFORMATIONAL,
            importance_score=0.88,
            urgency_score=0.5,
            data_mode=DataMode.LIVE,
            last_processed_at=datetime.now(UTC),
            model_version="gemini-2.0-flash",
            prompt_version="v1.0",
            schema_version="1.0.0",
            processing_run_id=uuid.uuid4(),
        )

        session.add_all([ev1, snap1, ev2, snap2, ev3, snap3, ev4, snap4])
        session.commit()

        yield session


@pytest.fixture
def client(test_db_session: Session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: test_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_no_location_filter_returns_all_events(client: TestClient):
    """When no location filter is active, all events (including national) are returned."""
    resp = client.get("/events?data_mode=live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["events"]) == 4


def test_province_filter_dki_jakarta_hierarchy(client: TestClient):
    """Filter 'DKI Jakarta' matches all events in DKI Jakarta (Jakarta Timur + Jakarta Barat)."""
    resp = client.get("/events?data_mode=live&location_province=DKI%20Jakarta")
    assert resp.status_code == 200
    data = resp.json()
    # DKI Jakarta contains Jaktim and Jakbar, but NOT Jogja or National
    assert data["total"] == 2
    headlines = [e["headline"] for e in data["events"]]
    assert any("Jakarta Timur" in h for h in headlines)
    assert any("Jakarta Barat" in h for h in headlines)
    assert not any("Yogyakarta" in h for h in headlines)
    assert not any("stimulus" in h for h in headlines)


def test_city_filter_jakarta_timur(client: TestClient):
    """Filter city 'Jakarta Timur' strictly returns only Jakarta Timur event."""
    resp = client.get("/events?data_mode=live&location_city=Jakarta%20Timur")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "Jakarta Timur" in data["events"][0]["headline"]


def test_legacy_location_province_with_city_name(client: TestClient):
    """If client sends location_province='Jakarta Timur', system gracefully matches the city."""
    resp = client.get("/events?data_mode=live&location_province=Jakarta%20Timur")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "Jakarta Timur" in data["events"][0]["headline"]


def test_generic_location_param(client: TestClient):
    """Parameter 'location' works across province, city, and canonical_name."""
    resp_prov = client.get("/events?data_mode=live&location=DKI%20Jakarta")
    assert resp_prov.status_code == 200
    assert resp_prov.json()["total"] == 2

    resp_city = client.get("/events?data_mode=live&location=Jakarta%20Timur")
    assert resp_city.status_code == 200
    assert resp_city.json()["total"] == 1


def test_strict_local_only_excludes_national_events(client: TestClient):
    """Per Decision A1.4: events with no location or country=Indonesia are excluded when a region is chosen."""
    resp = client.get("/events?data_mode=live&location=DKI%20Jakarta")
    assert resp.status_code == 200
    for ev in resp.json()["events"]:
        assert ev["primary_location"] is not None
        assert "DKI Jakarta" in ev["primary_location"]["province"]


def test_nonexistent_location_returns_empty_state_not_error(client: TestClient):
    """A non-existent location returns total: 0 and events: [], not an HTTP error."""
    resp = client.get("/events?data_mode=live&location=Papua%20Barat")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["events"] == []


def test_location_and_category_combination(client: TestClient):
    """Combining location and category filters correctly narrows the result set."""
    resp = client.get(
        "/events?data_mode=live&location=DKI%20Jakarta&category=disaster_and_weather"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    resp_policy = client.get(
        "/events?data_mode=live&location=DKI%20Jakarta&category=government_and_public_policy"
    )
    assert resp_policy.status_code == 200
    assert resp_policy.json()["total"] == 0
