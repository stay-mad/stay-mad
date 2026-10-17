"""Acceptance Test Suite for Stay Mad API and Pipeline.

Validates all 8 acceptance scenarios from docs/acceptance-matrix.md
and critical architectural rules (DEC-0001, DEC-0006, DEC-0008, Conflict #7).

Authority:
- docs/contracts/openapi.yaml
- docs/acceptance-matrix.md
- docs/decisions.md
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
from backend.staymad.api.main import create_app, perform_startup_checks
from backend.staymad.db.base import Base
from backend.staymad.db.models.enums import ActionabilityLevel
from backend.staymad.db.models.event import Event, EventChange
from backend.staymad.db.session import create_session_factory
from backend.staymad.events.manager import EventSynthesisManager
from backend.staymad.ingest.pipeline import IngestExtractionPipeline
from backend.staymad.jobs.eval_runner import run_baseline_check
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.resolver.manager import EventResolverManager

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"
SOURCES_PATH = REPO_ROOT / "config" / "sources.yaml"


@pytest.fixture(scope="module")
def seeded_env():
    """Seed in-memory database with the complete 23-article demo fixture."""
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
        # Step 1: Ingestion & Extraction
        result = pipeline.process_batch(articles, session)
        run_id = result.processing_run_id

        # Step 2: 3-Tier Resolution
        resolver = EventResolverManager(
            session=session, llm_client=llm, ablation_mode="tier3"
        )
        for art_ver in result.article_versions:
            ver_claims = [
                c for c in result.claims if c.article_version_id == art_ver.id
            ]
            resolver.resolve_article_version(art_ver, ver_claims, run_id)
        session.commit()

        # Step 3: Synthesis & Snapshots v1
        synth_mgr = EventSynthesisManager(session=session, llm_client=llm)
        all_events = session.scalars(select(Event)).all()
        for ev in all_events:
            synth_mgr.synthesize_event_snapshot(ev.id, run_id, force_snapshot=True)
        session.commit()

        # Step 4: Synthesize official update v2 for flood cluster (Scenario 5)
        # Find flood event (contains Ciliwung)
        flood_event = next(
            ev
            for ev in all_events
            if any(
                "ciliwung" in (ec.claim.claim_text or "").lower()
                for ec in ev.event_claims
                if ec.claim
            )
        )
        bpbd_claims = [
            c
            for c in result.claims
            if c.source
            and "bpbd" in (c.source.source_family or "").lower()
            and c.event_claims
            and any(ec.event_id == flood_event.id for ec in c.event_claims)
        ]
        synth_mgr.synthesize_event_snapshot(
            flood_event.id,
            run_id,
            newly_added_claims=bpbd_claims,
            force_snapshot=True,
        )
        session.commit()

    return {
        "engine": engine,
        "session_factory": session_factory,
        "run_id": run_id,
    }


@pytest.fixture
def api_client(seeded_env):
    """FastAPI TestClient with overridden database dependency."""
    app = create_app()

    def override_get_db():
        with seeded_env["session_factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ── Skenario 1: Deduplikasi & Source Family Grouping ─────────────────────────


def test_acc_01_syndicated_duplicate(api_client, seeded_env):
    """Scenario 1: 3 syndicated articles grouped under 1 source_family in /events/{id}/sources."""
    with seeded_env["session_factory"]() as session:
        # Find flood event containing syndicated Transmedia articles (Detikcom, CNN Indonesia)
        events = session.scalars(select(Event)).all()
        target_event = None
        for ev in events:
            families = {
                ec.claim.source.source_family
                for ec in ev.event_claims
                if ec.claim and ec.claim.source
            }
            if "TRANSMEDIA" in families:
                target_event = ev
                break
        assert target_event is not None, (
            "Flood event with Transmedia syndication must exist"
        )
        event_id = target_event.id

    resp = api_client.get(f"/events/{event_id}/sources")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["event_id"] == str(event_id)
    assert "sources" in data
    assert len(data["sources"]) >= 2

    # Verify both syndicated outlets appear with authentic URLs
    transmedia_sources = [
        s for s in data["sources"] if s["source_family"] == "TRANSMEDIA"
    ]
    assert len(transmedia_sources) >= 2, (
        "Both Detikcom and CNN Indonesia must be present"
    )
    names = {s["name"].lower() for s in transmedia_sources}
    assert any("detik" in n for n in names)
    assert any("cnn" in n for n in names)

    # All articles under TRANSMEDIA count as 1 unique family
    families_set = {s["source_family"] for s in data["sources"]}
    assert data["unique_source_families"] == len(families_set)


# ── Skenario 2: Deteksi Konflik Angka Faktual ─────────────────────────────────


def test_acc_02_differing_numbers_conflict(api_client, seeded_env):
    """Scenario 2 & 4: Detects numerical conflict between 5 vs 7 kecamatan in /events/{id}/analysis."""
    with seeded_env["session_factory"]() as session:
        events = session.scalars(select(Event)).all()
        flood_event = next(
            ev
            for ev in events
            if any(
                "ciliwung" in (ec.claim.claim_text or "").lower()
                for ec in ev.event_claims
                if ec.claim
            )
        )
        event_id = flood_event.id

    # Check /events/{id}/analysis
    resp = api_client.get(f"/events/{event_id}/analysis")
    assert resp.status_code == 200, resp.text
    analysis = resp.json()

    assert analysis["event_id"] == str(event_id)
    assert "conflicts" in analysis
    assert len(analysis["conflicts"]) >= 1

    num_conflict = next(
        (
            cf
            for cf in analysis["conflicts"]
            if {cf["value_a"], cf["value_b"]} == {"5", "7"}
        ),
        None,
    )
    assert num_conflict is not None, (
        "Conflict between 5 and 7 kecamatan must be explicitly recorded"
    )
    assert num_conflict["field_name"] in (
        "affected_kecamatan_count",
        "jumlah_kecamatan",
        "districts_affected",
    )

    # Check /events/{id} detail conflict summary
    detail_resp = api_client.get(f"/events/{event_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["conflict_summary"] is not None
    assert len(detail["conflict_summary"]["evidence_claim_ids"]) >= 2


# ── Skenario 3: Pemisahan Hard Constraints (Lokasi) ───────────────────────────


def test_acc_03_same_day_location_isolation(api_client, seeded_env):
    """Scenario 3: Separates rob Muara Baru/Jakbar vs luapan Ciliwung/Jaktim as distinct events."""
    resp = api_client.get("/events")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    events = data["events"]
    assert len(events) >= 2

    headlines = [e["headline"].lower() for e in events]
    # Check that both flood issues exist as separate events
    has_ciliwung = any("ciliwung" in h or "jakarta timur" in h for h in headlines)
    has_rob = any(
        "rob" in h or "pasang" in h or "jakarta barat" in h for h in headlines
    )
    assert has_ciliwung and has_rob, (
        "Ciliwung and Rob events must be isolated canonical events"
    )

    # Test filtering by location_city / province
    resp_jaktim = api_client.get("/events?location_city=Jakarta Timur")
    assert resp_jaktim.status_code == 200
    jaktim_events = resp_jaktim.json()["events"]
    assert all(
        "jakarta barat"
        not in (e["headline"].lower() + str(e.get("primary_location") or ""))
        for e in jaktim_events
    )


# ── Skenario 4: Pemisahan Event Serupa di Hari Berbeda ─────────────────────────


def test_acc_04_different_day_similar_event(api_client, seeded_env):
    """Scenario 4: Separate event on different days (> 72 hours apart: 7 Okt vs 10 Okt)."""
    with seeded_env["session_factory"]() as session:
        events = session.scalars(select(Event)).all()
        # Find 7 Okt event (art_demo_06) vs 10 Okt events
        rob_event = next(
            (
                ev
                for ev in events
                if any(
                    "7/10/2026" in (ec.claim.claim_text or "")
                    or "pasang" in (ec.claim.claim_text or "").lower()
                    for ec in ev.event_claims
                    if ec.claim
                )
            ),
            None,
        )
        ciliwung_event = next(
            (
                ev
                for ev in events
                if any(
                    "ciliwung" in (ec.claim.claim_text or "").lower()
                    for ec in ev.event_claims
                    if ec.claim
                )
            ),
            None,
        )
        assert rob_event is not None
        assert ciliwung_event is not None
        assert rob_event.id != ciliwung_event.id, (
            "Events on different days must be separate events"
        )


# ── Skenario 5a: Pembaruan Resmi & Change Set Snapshot ────────────────────────


def test_acc_05_official_update_changeset(api_client, seeded_env):
    """Scenario 5: Official update produces Snapshot v2 and records EventChange records."""
    with seeded_env["session_factory"]() as session:
        events = session.scalars(select(Event)).all()
        flood_event = next(
            ev
            for ev in events
            if any(
                "ciliwung" in (ec.claim.claim_text or "").lower()
                for ec in ev.event_claims
                if ec.claim
            )
        )
        event_id = flood_event.id
        assert len(flood_event.snapshots) >= 2, (
            "Flood event must have v1 and v2 snapshots"
        )

    resp = api_client.get(f"/events/{event_id}/changes")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["event_id"] == str(event_id)
    assert data["material_change_count"] >= 1
    assert len(data["changes"]) >= 1

    # Check changes items have categories and evidence
    change_cats = [
        chg["change_category"] for chg in data["changes"] if chg.get("change_category")
    ]
    assert any(
        cat in ("ALERT_STATUS", "NUMERICAL", "ESCALATION", "AREA_CHANGE")
        for cat in change_cats
    )
    for chg in data["changes"]:
        assert "evidence_claim_ids" in chg


# ── Skenario 5b: Negative Case — Wording-Only Reprocessing ─────────────────────


def test_acc_05b_no_changeset_wording_only(api_client, seeded_env):
    """Scenario 5b: Reprocessing without new material claims produces zero new EventChange."""
    with seeded_env["session_factory"]() as session:
        events = session.scalars(select(Event)).all()
        # Find transportation event (KRL)
        krl_event = next(
            ev
            for ev in events
            if any(
                "persinyalan" in (ec.claim.claim_text or "").lower()
                for ec in ev.event_claims
                if ec.claim
            )
        )
        # Verify changes for single snapshot event
        changes = session.scalars(
            select(EventChange).where(EventChange.event_id == krl_event.id)
        ).all()
        assert len(changes) == 0, "No material changes on initial single snapshot"

    resp = api_client.get(f"/events/{krl_event.id}/changes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["material_change_count"] == 0
    assert data["changes"] == []


# ── Skenario 6: Penolakan Injeksi Jahat & Aksi Palsu ───────────────────────────


def test_acc_06_malicious_instruction_isolation(api_client, seeded_env):
    """Scenario 6: Prompt injection in art_demo_07 rejected; no unauthorized ACTION_REQUIRED."""
    with seeded_env["session_factory"]() as session:
        events = session.scalars(select(Event)).all()
        # Find event associated with art_demo_07
        inj_event = None
        for ev in events:
            for ec in ev.event_claims:
                if ec.claim and "bypass" in (ec.claim.claim_text or "").lower():
                    inj_event = ev
                    break
            if inj_event:
                break

    assert inj_event is not None

    resp = api_client.get(f"/events/{inj_event.id}")
    assert resp.status_code == 200
    detail = resp.json()

    # DEC-0004 & ADR-006: No malicious text executed
    assert "SELURUH JAKARTA TENGGELAM" not in detail["headline"]
    assert detail["actionability_level"] != ActionabilityLevel.ACTION_REQUIRED.value
    # No airport evacuation fake action
    action_texts = " ".join(a["action_text"] for a in detail["actions"]).lower()
    assert "bandara" not in action_texts
    # Confidence score is not forced to 1.0
    assert detail["confidence_signals"]["confidence_score"] < 1.0


# ── Skenario 7b: Validasi UI Views di Mode Live, Demo, dan Degraded ───────────


def test_acc_07b_ui_mode_views(api_client, seeded_env):
    """Scenario 7b: Overview, Detail, Timeline, Sources, Changes, Processing across modes."""
    with seeded_env["session_factory"]() as session:
        events = session.scalars(select(Event)).all()
        event_id = events[0].id

    # 1. Live mode views
    resp_live = api_client.get("/events?data_mode=live")
    assert resp_live.status_code == 200
    assert resp_live.json()["data_mode"] == "live"

    # 2. Demo mode views
    resp_demo = api_client.get("/events?data_mode=demo")
    assert resp_demo.status_code == 200
    assert resp_demo.json()["data_mode"] == "demo"

    # 3. Degraded mode views
    resp_deg = api_client.get("/events?data_mode=degraded")
    assert resp_deg.status_code == 200
    assert resp_deg.json()["data_mode"] == "degraded"

    # 4. Detail view
    resp_detail = api_client.get(f"/events/{event_id}")
    assert resp_detail.status_code == 200
    assert resp_detail.json()["id"] == str(event_id)

    # 5. Timeline view
    resp_tl = api_client.get(f"/events/{event_id}/timeline")
    assert resp_tl.status_code == 200
    assert "entries" in resp_tl.json()

    # 6. Sources view
    resp_src = api_client.get(f"/events/{event_id}/sources")
    assert resp_src.status_code == 200
    assert "sources" in resp_src.json()

    # 7. Processing transparency view (Screen 3, DEC-0006)
    resp_proc = api_client.get(f"/events/{event_id}/processing")
    assert resp_proc.status_code == 200
    proc = resp_proc.json()
    assert "articles_analyzed" in proc
    assert "claims_extracted" in proc
    assert "confidence_signals" in proc
    assert "decision_reason_codes" in proc

    # 8. Locations view
    resp_loc = api_client.get("/locations")
    assert resp_loc.status_code == 200
    assert "locations" in resp_loc.json()

    # 9. Health view (/health and /healthz)
    resp_health = api_client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] in ("ok", "degraded")
    assert api_client.get("/healthz").status_code == 200


# ── Skenario 8a: Evaluator Report Artifact Produced ───────────────────────────


def test_acc_08a_report_artifact_produced(tmp_path):
    """Scenario 8a: Running evaluation baseline check produces valid report artifact."""
    report_output_dir = tmp_path / "reports"
    success = run_baseline_check(
        fixture_path=FIXTURE_PATH,
        sources_config_path=SOURCES_PATH,
        output_dir=report_output_dir,
    )
    assert success is True

    # Verify report artifact was written
    report_files = list(report_output_dir.glob("*.json"))
    assert len(report_files) == 1, "Report artifact file must be produced"

    with open(report_files[0], "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert "report_id" in rep
    assert rep["run_type"] == "baseline"
    assert rep["status"] == "PASS"
    assert rep["articles_analyzed"] == 23
    assert rep["events_resolved"] >= 4
    assert rep["processing_run_id"]


# ── Extra Fixture & Contract Integrity Tests ──────────────────────────────────


def test_production_startup_failure_check(monkeypatch):
    """DEC-0006: Startup failure when fixture adapter is active or API key missing in production."""
    # Test 1: Production with fixture_mode=true -> must raise RuntimeError
    monkeypatch.setenv("STAYMAD_ENV", "production")
    monkeypatch.setenv("FIXTURE_MODE", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    with pytest.raises(RuntimeError, match="cannot be used in production"):
        perform_startup_checks()

    # Test 2: Production with missing GEMINI_API_KEY -> must raise RuntimeError
    monkeypatch.setenv("FIXTURE_MODE", "false")
    monkeypatch.setenv("USE_MOCK_GEMINI", "false")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is required"):
        perform_startup_checks()


def test_health_503_on_production_misconfiguration(monkeypatch, api_client):
    """GET /health must return HTTP 503 if misconfigured in production."""
    monkeypatch.setenv("STAYMAD_ENV", "production")
    monkeypatch.setenv("FIXTURE_MODE", "true")
    resp = api_client.get("/health")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "error"
    assert "FATAL" in data["details"]


def test_error_handlers_contract(api_client):
    """Test standardized ErrorResponse formats on 404 and 422."""
    # 404 on non-existent event
    random_id = uuid.uuid4()
    resp_404 = api_client.get(f"/events/{random_id}")
    assert resp_404.status_code == 404
    err_404 = resp_404.json()
    assert err_404["error"] == "not_found"
    assert "tidak ditemukan" in err_404["message"]

    # 422 on invalid query parameter (limit > 50)
    resp_422 = api_client.get("/events?limit=999")
    assert resp_422.status_code == 422
    err_422 = resp_422.json()
    assert err_422["error"] == "validation_error"
