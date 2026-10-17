"""Unit tests for Stage 04: 3-Tier Hybrid Event Resolver, Canonical Clustering, and Ablation.

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D), ADR-005, ADR-007
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.staymad.db.base import Base
from backend.staymad.db.models.audit import EventMembershipAudit
from backend.staymad.db.models.enums import ResolutionDecision
from backend.staymad.db.models.event import Event
from backend.staymad.db.session import create_db_engine, create_session_factory
from backend.staymad.ingest.pipeline import IngestExtractionPipeline
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.resolver.config import ResolverConfig
from backend.staymad.resolver.manager import EventResolverManager
from backend.staymad.resolver.tier1_deterministic import (
    ArticleCandidate,
    EventAnchor,
    check_hard_constraints,
    compute_content_hash,
    group_candidates_by_source_family,
    is_content_duplicate,
)
from backend.staymad.resolver.tier2_embedding import (
    DeterministicEmbeddingGenerator,
    compute_composite_score,
    cosine_similarity,
    evaluate_tier2_threshold,
)

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


def test_resolver_config_loaded_properly():
    """Verify config/resolver.yaml contains all required parameters for all 3 tiers."""
    cfg = ResolverConfig.load()

    # Tier 1 parameters
    assert cfg.hard.time_incompatible_hours == 72.0
    assert cfg.hard.strict_category is True

    # Tier 2 parameters
    assert cfg.embedding.top_k == 10
    assert cfg.embedding.min_cosine == 0.20
    assert cfg.embedding.vector_dimension == 768
    assert cfg.embedding.model_name == "text-multilingual-embedding-002"
    assert cfg.scoring.w_semantic == 0.40
    assert cfg.scoring.w_time == 0.30
    assert cfg.scoring.w_location == 0.20
    assert cfg.scoring.w_entity == 0.10
    assert cfg.scoring.time_decay_hours == 48.0
    assert cfg.thresholds.low == 0.35
    assert cfg.thresholds.high == 0.75

    # Tier 3 parameters
    assert cfg.adjudication.max_candidates_per_call == 5
    assert cfg.adjudication.needs_review_confidence_cutoff == 0.60


def test_tier1_hard_constraint_category_mismatch():
    """Articles with mismatched category must be rejected under strict_category."""
    cfg = ResolverConfig.load()
    cand = ArticleCandidate(
        article_version_id="art-1",
        category="government_and_public_policy",
        title="Pemerintah Evaluasi Subsidi Transportasi",
    )
    anchor = EventAnchor(
        event_id="evt-1",
        category="disaster_and_weather",
        headline="Banjir Jakarta Timur",
    )

    passed, reason = check_hard_constraints(cand, anchor, cfg)
    assert not passed
    assert reason == "CAT_MISMATCH"


def test_tier1_hard_constraint_time_incompatible():
    """Articles separated by more than 72 hours must fail TIME_INCOMPATIBLE."""
    cfg = ResolverConfig.load()
    t1 = datetime(2026, 10, 10, 8, 0, tzinfo=UTC)
    t2 = t1 + timedelta(hours=75)  # > 72 hours

    cand = ArticleCandidate(
        article_version_id="art-1",
        category="disaster_and_weather",
        published_time=t2,
    )
    anchor = EventAnchor(
        event_id="evt-1",
        category="disaster_and_weather",
        time_window_center=t1,
    )

    passed, reason = check_hard_constraints(cand, anchor, cfg)
    assert not passed
    assert reason == "TIME_INCOMPATIBLE"


def test_tier1_hard_constraint_location_incompatible():
    """Articles with conflicting provinces or disjoint localized cities must fail LOC_INCOMPATIBLE."""
    cfg = ResolverConfig.load()
    # Different provinces (Jawa Tengah vs DKI Jakarta)
    cand_merapi = ArticleCandidate(
        article_version_id="art-1",
        category="disaster_and_weather",
        location_raw="Gunung Merapi, Magelang, Jawa Tengah",
    )
    anchor_flood = EventAnchor(
        event_id="evt-1",
        category="disaster_and_weather",
        primary_location_name="Jakarta Timur, DKI Jakarta",
    )
    passed, reason = check_hard_constraints(cand_merapi, anchor_flood, cfg)
    assert not passed
    assert reason == "LOC_INCOMPATIBLE"

    # Distinct cities within DKI Jakarta (Jakarta Barat rob vs Jakarta Timur flood)
    cand_jakbar = ArticleCandidate(
        article_version_id="art-2",
        category="disaster_and_weather",
        location_raw="Rawa Buaya, Jakarta Barat",
    )
    passed_jb, reason_jb = check_hard_constraints(cand_jakbar, anchor_flood, cfg)
    assert not passed_jb
    assert reason_jb == "LOC_INCOMPATIBLE"


def test_tier1_content_deduplication():
    """Identical content hashes must be detected."""
    t1 = "Banjir melanda Cipinang Melayu"
    e1 = "Air setinggi 80 cm merendam ratusan rumah warga."

    h1 = compute_content_hash(t1, e1)
    h2 = compute_content_hash(t1, e1)
    assert h1 == h2

    pool = {h1}
    assert is_content_duplicate(h1, pool)
    assert not is_content_duplicate(
        compute_content_hash("Judul lain", "Cuplikan"), pool
    )


def test_tier1_source_family_grouping():
    """Group articles by source family to prevent consensus inflation."""
    c1 = ArticleCandidate(article_version_id="1", source_family="TRANSMEDIA")
    c2 = ArticleCandidate(article_version_id="2", source_family="TRANSMEDIA")
    c3 = ArticleCandidate(article_version_id="3", source_family="LKBN_ANTARA")

    grouped = group_candidates_by_source_family([c1, c2, c3])
    assert len(grouped["TRANSMEDIA"]) == 2
    assert len(grouped["LKBN_ANTARA"]) == 1


def test_tier2_embedding_cosine_similarity():
    """Verify 768-dim embedding generation and cosine similarity behavior."""
    emb_gen = DeterministicEmbeddingGenerator()
    v1 = emb_gen.embed_text(
        "Banjir luapan Kali Ciliwung Jakarta Timur rendam ratusan rumah"
    )
    v2 = emb_gen.embed_text(
        "Hujan lebat Jakarta Timur akibatkan banjir luapan Kali Ciliwung"
    )
    v3 = emb_gen.embed_text(
        "Gunung Merapi luncurkan awan panas guguran ke arah Magelang"
    )

    assert len(v1) == 768
    assert len(v2) == 768
    assert len(v3) == 768

    # Similar topics should have higher similarity than completely distinct topics
    sim_similar = cosine_similarity(v1, v2)
    sim_different = cosine_similarity(v1, v3)

    assert sim_similar > 0.40
    assert sim_different < 0.20
    assert sim_similar > sim_different


def test_tier2_composite_scoring_and_thresholds():
    """Verify composite candidate score calculation and thresholds."""
    cfg = ResolverConfig.load()
    t = datetime(2026, 10, 10, 8, 30, tzinfo=UTC)

    emb_gen = DeterministicEmbeddingGenerator()
    emb_anchor = emb_gen.embed_text("Banjir Jakarta Timur Ciliwung")
    emb_match = emb_gen.embed_text("Banjir Jakarta Timur Ciliwung luapan air")

    anchor = EventAnchor(
        event_id="evt-1",
        category="disaster_and_weather",
        time_window_center=t,
        city="Jakarta Timur",
        province="DKI Jakarta",
        entities=["BPBD DKI", "Kali Ciliwung"],
        embedding=emb_anchor,
    )

    cand_high = ArticleCandidate(
        article_version_id="cand-high",
        category="disaster_and_weather",
        published_time=t + timedelta(minutes=30),
        city="Jakarta Timur",
        province="DKI Jakarta",
        entities=["BPBD DKI", "Kali Ciliwung"],
        embedding=emb_match,
    )

    score_high, signals_high = compute_composite_score(cand_high, anchor, cfg)
    assert score_high >= cfg.thresholds.high
    assert signals_high["location_match"] is True
    assert evaluate_tier2_threshold(score_high, cfg) == "SAME_EVENT"

    # Low score candidate
    emb_low = emb_gen.embed_text(
        "Kebijakan subsidi transportasi kereta api kementerian"
    )
    cand_low = ArticleCandidate(
        article_version_id="cand-low",
        category="disaster_and_weather",
        published_time=t + timedelta(hours=40),
        city="Surabaya",
        province="Jawa Timur",
        entities=["Kemenhub"],
        embedding=emb_low,
    )

    score_low, signals_low = compute_composite_score(cand_low, anchor, cfg)
    assert score_low < cfg.thresholds.low
    assert signals_low["location_match"] is False
    assert evaluate_tier2_threshold(score_low, cfg) == "SEPARATE_EVENT"


def test_transitive_cluster_guard():
    """Articles must be verified against canonical anchor evidence, avoiding transitive chaining."""
    cfg = ResolverConfig.load()
    emb_gen = DeterministicEmbeddingGenerator()

    # Anchor event: Banjir Cipinang Melayu Jakarta Timur
    anchor = EventAnchor(
        event_id="anchor-flood",
        category="disaster_and_weather",
        headline="Banjir Cipinang Melayu Jakarta Timur",
        primary_location_name="Jakarta Timur",
        city="Jakarta Timur",
        province="DKI Jakarta",
        embedding=emb_gen.embed_text("Banjir Cipinang Melayu Jakarta Timur"),
        representative_claims=["Banjir rendam Cipinang Melayu Jakarta Timur"],
    )

    # Candidate 1 is about Cipinang Melayu
    c1 = ArticleCandidate(
        article_version_id="cand-1",
        category="disaster_and_weather",
        city="Jakarta Timur",
        province="DKI Jakarta",
        title="Cipinang Melayu terendam banjir",
        excerpt="Genangan air di Cipinang Melayu mencapai 80 cm.",
        embedding=emb_gen.embed_text("Cipinang Melayu terendam banjir"),
    )
    score1, _ = compute_composite_score(c1, anchor, cfg)
    assert score1 >= 0.50

    # Candidate 2 is about distant place in Banten (Tangerang banjir)
    c2 = ArticleCandidate(
        article_version_id="cand-2",
        category="disaster_and_weather",
        city="Tangerang",
        province="Banten",
        title="Banjir di Tangerang Banten",
        excerpt="Genangan air di perumahan Ciledug Tangerang.",
        embedding=emb_gen.embed_text("Banjir di Tangerang Banten"),
    )
    # Direct check against canonical anchor must reject it (LOC_INCOMPATIBLE)
    passed, reason = check_hard_constraints(c2, anchor, cfg)
    assert not passed
    assert reason == "LOC_INCOMPATIBLE"


def test_seed_23_clustering_and_acceptance_scenarios(db_session):
    """Run full Ingest + 3-Tier Resolution on the 23 seed demo articles.

    Verifies:
    - Cluster A (Jakarta Flood), Cluster B (Merapi Volcano), Cluster C (KRL), Cluster D (Policy).
    - test_acc_03: Rob flood Jakarta Barat on different day is separated (acceptance_scenario 3).
    - test_acc_04: Number conflict 7 vs 5 kecamatan merged into same event (acceptance_scenario 4).
    - Audit records: EventMembershipAudit created for every article version.
    """
    assert FIXTURE_PATH.exists(), f"Fixture not found at {FIXTURE_PATH}"
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    articles = fixture_data.get("articles", [])
    assert len(articles) == 23

    # Step 1: Ingest & Extract
    llm = DeterministicGeminiClient()
    pipeline = IngestExtractionPipeline(llm_client=llm)
    ingest_result = pipeline.process_batch(articles, db_session)
    assert ingest_result.articles_saved == 23

    # Step 2: 3-Tier Event Resolution
    resolver = EventResolverManager(
        session=db_session,
        llm_client=llm,
        ablation_mode="tier3",
    )

    run_id = ingest_result.processing_run_id
    results = []
    for art_ver in ingest_result.article_versions:
        # Load claims for this version
        claims = [c for c in ingest_result.claims if c.article_version_id == art_ver.id]
        res = resolver.resolve_article_version(art_ver, claims, run_id)
        results.append((art_ver, res))

    db_session.commit()

    # Step 3: Validate Clusters & Scenarios
    # Map results by article title / id
    events_created = db_session.scalars(select(Event)).all()
    assert len(events_created) >= 4, "Must generate at least 4 primary canonical events"

    audits = db_session.scalars(select(EventMembershipAudit)).all()
    assert len(audits) == 23, "Every article must have an EventMembershipAudit entry"

    # Acceptance Scenario 3 check: art_demo_06 (rob flood Jakarta Barat on diff day)
    # Must be separate event from main Jakarta Timur flood event
    art_demo_01_res = next(
        r for v, r in results if "5 Kecamatan di Jakarta Timur" in v.title
    )
    art_demo_06_res = next(r for v, r in results if "Genangan Pasang Rob" in v.title)

    assert art_demo_01_res.event_id != art_demo_06_res.event_id, (
        "Scenario 3: Jakarta Barat rob flood on different day must NOT be merged with Jakarta Timur flood"
    )

    # Acceptance Scenario 4 check: art_demo_02 (7 kecamatan vs 5 kecamatan number conflict)
    # Must be merged into same Jakarta Timur flood event
    art_demo_02_res = next(r for v, r in results if "7 Kecamatan Terdampak" in v.title)
    assert art_demo_01_res.event_id == art_demo_02_res.event_id, (
        "Scenario 4: Number conflict reporting on same flood event must be merged into same event"
    )

    # Verify audit signals recorded
    for a in audits:
        assert a.decision in (
            ResolutionDecision.SAME_EVENT,
            ResolutionDecision.SEPARATE_EVENT,
            ResolutionDecision.RELATED_EVENT,
            ResolutionDecision.NEEDS_REVIEW,
        )
        assert a.processing_run_id == run_id


def test_ablation_study_tiers(db_session):
    """Verify that all three ablation modes (tier1, tier2, tier3) execute properly."""
    c1 = ArticleCandidate(
        article_version_id=str(uuid.uuid4()),
        category="disaster_and_weather",
        title="Banjir rendam Cipinang Melayu Jakarta Timur",
        excerpt="Luapan air merendam ratusan rumah di Cipinang Melayu Jakarta Timur.",
        city="Jakarta Timur",
        province="DKI Jakarta",
        published_time=datetime(2026, 10, 10, 8, 0, tzinfo=UTC),
    )
    c2 = ArticleCandidate(
        article_version_id=str(uuid.uuid4()),
        category="disaster_and_weather",
        title="Kali Ciliwung meluap di Jakarta Timur",
        excerpt="Air meluap menggenangi jalan di Jakarta Timur.",
        city="Jakarta Timur",
        province="DKI Jakarta",
        published_time=datetime(2026, 10, 10, 9, 0, tzinfo=UTC),
    )

    run_id = uuid.uuid4()

    # Test tier1 ablation mode
    mgr_t1 = EventResolverManager(session=db_session, ablation_mode="tier1")
    res1_t1 = mgr_t1.resolve_article(c1, run_id)
    assert res1_t1.tier_used == "TIER_1"
    assert res1_t1.is_new_event

    res2_t1 = mgr_t1.resolve_article(c2, run_id)
    assert res2_t1.tier_used == "TIER_1"
    assert res2_t1.decision == ResolutionDecision.SAME_EVENT

    # Test tier2 ablation mode
    mgr_t2 = EventResolverManager(session=db_session, ablation_mode="tier2")
    c3 = ArticleCandidate(
        article_version_id=str(uuid.uuid4()),
        category="transportation_and_infrastructure",
        title="KRL Stasiun Manggarai Alami Gangguan",
        excerpt="Persinyalan KRL di Manggarai bermasalah.",
        published_time=datetime(2026, 10, 11, 8, 0, tzinfo=UTC),
    )
    res3_t2 = mgr_t2.resolve_article(c3, run_id)
    assert res3_t2.is_new_event

    # Test tier3 ablation mode
    mgr_t3 = EventResolverManager(session=db_session, ablation_mode="tier3")
    c4 = ArticleCandidate(
        article_version_id=str(uuid.uuid4()),
        category="government_and_public_policy",
        title="Subsidi Transportasi Diperbarui Presiden",
        excerpt="Perpres diteken mengenai integrasi tarif.",
        published_time=datetime(2026, 10, 11, 10, 0, tzinfo=UTC),
    )
    res4_t3 = mgr_t3.resolve_article(c4, run_id)
    assert res4_t3.is_new_event
