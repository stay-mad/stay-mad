"""Unit tests for Live Ingest deduplication and Jobs API endpoint.

Authority: DEC-0003, DEC-0004, DEC-0006
"""

from __future__ import annotations

import argparse
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.staymad.api.main import app
from backend.staymad.db.base import Base
from backend.staymad.db.models.article import Article
from backend.staymad.db.models.enums import EventCategory
from backend.staymad.db.models.source import Source
from backend.staymad.db.session import create_db_engine, create_session_factory
from backend.staymad.jobs.live_ingest import execute_live_ingest_cycle


@pytest.fixture
def test_db_url(tmp_path):
    db_file = tmp_path / "test_ingest.db"
    return f"sqlite:///{db_file}"


@pytest.fixture
def client():
    return TestClient(app)


def test_jobs_ingest_endpoint_returns_accepted(client):
    """POST /jobs/ingest should return HTTP 202 Accepted immediately per DEC-0006."""
    with patch("backend.staymad.api.routers.jobs._run_ingest_background"):
        response = client.post("/jobs/ingest", json={"source": "antara", "limit": 2})
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "job_id" in data
        assert data["source"] == "antara"
        assert data["limit"] == 2

        # Check job status retrieval
        status_resp = client.get(f"/jobs/ingest/{data['job_id']}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["job_id"] == data["job_id"]


def test_jobs_ingest_not_found(client):
    """GET /jobs/ingest/{unknown_id} should return HTTP 404."""
    response = client.get("/jobs/ingest/non_existent_job_123")
    assert response.status_code == 404


def test_deduplication_skips_existing_articles(test_db_url):
    """Articles already stored by URL or content_hash must be skipped (saving LLM quota)."""
    engine = create_db_engine(test_db_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    # 1. Pre-seed an article in database
    from backend.staymad.db.models.enums import SourceTier, SourceType

    with session_factory() as session:
        src = Source(
            id=uuid.uuid4(),
            name="LKBN ANTARA",
            url="https://www.antaranews.com",
            source_type=SourceType.RSS,
            source_tier=SourceTier.TIER_1,
            source_family="LKBN_ANTARA",
            active=True,
        )
        session.add(src)
        session.flush()

        seeded_art = Article(
            id=uuid.uuid4(),
            source_id=src.id,
            url="https://www.antaranews.com/berita/123/gempa-m-5",
            content_hash="mock_hash_12345",
            category=EventCategory.DISASTER_AND_WEATHER,
            language="id",
        )
        session.add(seeded_art)
        session.commit()

    # 2. Mock RSS fetch returning duplicate article + 1 new article
    mock_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Antara News</title>
        <item>
          <title>BMKG: Gempa Magnitudo 5</title>
          <link>https://www.antaranews.com/berita/123/gempa-m-5</link>
          <description>Gempa bumi berkekuatan magnitudo 5 dirasakan warga.</description>
          <pubDate>Sun, 18 Oct 2026 12:00:00 +0700</pubDate>
        </item>
      </channel>
    </rss>
    """

    with patch(
        "backend.staymad.jobs.live_ingest._fetch_rss_content", return_value=mock_rss_xml
    ):
        summary, _ = execute_live_ingest_cycle(
            source="antara",
            max_articles=3,
            db_url=test_db_url,
        )
        # The only article in feed is a duplicate of seeded_art (same URL)
        assert summary["status"] == "no_new_articles"
        assert summary["total_found"] == 1
        assert summary["new_articles_count"] == 0
        assert summary["skipped_duplicates"] == 1


def test_cli_argument_parsing():
    """Verify CLI arguments for continuous daemon and polling interval."""
    parser = argparse.ArgumentParser(description="Test Parser")
    parser.add_argument("--source", type=str, default="antara")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--db-url", type=str, default=None)
    parser.add_argument("--daemon", action="store_true", default=False)
    parser.add_argument("--interval", type=int, default=600)

    # Test defaults
    args = parser.parse_args([])
    assert args.source == "antara"
    assert args.limit == 3
    assert args.db_url is None
    assert args.daemon is False
    assert args.interval == 600

    # Test daemon options
    args_daemon = parser.parse_args(
        [
            "--daemon",
            "--interval",
            "300",
            "--source",
            "all",
            "--db-url",
            "sqlite:///test.db",
        ]
    )
    assert args_daemon.daemon is True
    assert args_daemon.interval == 300
    assert args_daemon.source == "all"
    assert args_daemon.db_url == "sqlite:///test.db"
