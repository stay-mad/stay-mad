"""Unit tests for SQLAlchemy models and database schema."""

from __future__ import annotations

import uuid

from backend.staymad.db import (
    Action,
    Article,
    ArticleVersion,
    Base,
    Claim,
    Conflict,
    Event,
    EventChange,
    EventClaim,
    EventMembershipAudit,
    EventRelation,
    EventSnapshot,
    Location,
    ProcessingJob,
    ProcessingRun,
    Source,
    TimelineEntry,
)
from backend.staymad.db.models.enums import (
    ActionabilityLevel,
    ActionSourceType,
    ChangeType,
    ConfidenceBucket,
    DataMode,
    EventCategory,
    EventClaimRole,
    EventRelationType,
    EvidenceStatus,
    GeoLevel,
    JobStatus,
    JobType,
    ProcessingStage,
    ResolutionDecision,
    RunStatus,
    SourceTier,
    SourceType,
    TimelinePrecision,
    VerificationLevel,
)


def test_metadata_contains_all_16_entities():
    expected_tables = {
        "sources",
        "articles",
        "article_versions",
        "locations",
        "claims",
        "events",
        "event_snapshots",
        "event_changes",
        "event_claims",
        "event_membership_audits",
        "timeline_entries",
        "conflicts",
        "actions",
        "processing_runs",
        "processing_jobs",
        "event_relations",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert len(registered_tables) == 16, (
        f"Expected 16 tables, got {len(registered_tables)}"
    )
    assert registered_tables == expected_tables


def test_all_tables_have_uuid_primary_key():
    for table_name, table in Base.metadata.tables.items():
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["id"], (
            f"Table {table_name} must have primary key column 'id'"
        )


def test_claim_embedding_vector_dimension():
    claim_table = Base.metadata.tables["claims"]
    embedding_col = claim_table.c.embedding
    assert embedding_col is not None, "Claim must have an embedding column"
    # Type should be pgvector Vector of dimension 768 per ADR-007
    assert hasattr(embedding_col.type, "dim"), (
        "Embedding column must be pgvector Vector type"
    )
    assert embedding_col.type.dim == 768, (
        f"Expected vector dimension 768, got {embedding_col.type.dim}"
    )


def test_model_instantiations():
    # Source
    src = Source(
        id=uuid.uuid4(),
        name="Test BMKG",
        url="https://bmkg.go.id",
        source_type=SourceType.API,
        source_tier=SourceTier.TIER_1,
        source_family="GOV_BMKG",
        rate_limit_per_min=60,
        active=True,
    )
    assert src.name == "Test BMKG"

    # Article
    art = Article(
        id=uuid.uuid4(),
        source_id=src.id,
        url="https://bmkg.go.id/news/1",
        content_hash="abc123456789",
        category=EventCategory.DISASTER_AND_WEATHER,
        language="id",
    )
    assert art.category == EventCategory.DISASTER_AND_WEATHER

    # ArticleVersion
    ver = ArticleVersion(
        id=uuid.uuid4(),
        article_id=art.id,
        title="Gempa M5.0",
        excerpt="Gempa bumi berkekuatan 5.0",
        content_hash="abc123456789",
        schema_version="1.0",
    )
    assert ver.title == "Gempa M5.0"

    # Location
    loc = Location(
        id=uuid.uuid4(),
        city="Jakarta Timur",
        province="DKI Jakarta",
        country="Indonesia",
        geo_level=GeoLevel.CITY,
        canonical_name="Jakarta Timur, DKI Jakarta",
        source_text="Jakarta Timur",
    )
    assert loc.canonical_name == "Jakarta Timur, DKI Jakarta"

    # ProcessingRun
    run = ProcessingRun(
        id=uuid.uuid4(),
        stage=ProcessingStage.INGEST,
        status=RunStatus.RUNNING,
        articles_processed=1,
        model_version="gemini-2.0-flash",
        prompt_version="1.0",
        schema_version="1.0",
    )
    assert run.status == RunStatus.RUNNING

    # Claim
    clm = Claim(
        id=uuid.uuid4(),
        article_version_id=ver.id,
        source_id=src.id,
        claim_text="Gempa bumi terjadi pada kedalaman 10 km.",
        source_span="Gempa bumi berkekuatan 5.0 pada kedalaman 10 km.",
        extraction_confidence=0.95,
        event_time_precision=TimelinePrecision.EXACT,
        model_version="gemini-2.0-flash",
        prompt_version="1.0",
        schema_version="1.0",
        processing_run_id=run.id,
    )
    assert clm.source_span.startswith("Gempa")

    # Event
    evt = Event(
        id=uuid.uuid4(),
        event_type="earthquake",
        category=EventCategory.DISASTER_AND_WEATHER,
        primary_location_id=loc.id,
    )
    assert evt.event_type == "earthquake"

    # EventSnapshot
    snap = EventSnapshot(
        id=uuid.uuid4(),
        event_id=evt.id,
        version_number=1,
        headline="Gempa M5.0 Guncang Jakarta Timur",
        what_happened="Gempa berkekuatan M5.0 tercatat di kedalaman 10 km.",
        confidence_score=0.92,
        confidence_bucket=ConfidenceBucket.HIGH,
        evidence_status=EvidenceStatus.SUPPORTED,
        verification_level=VerificationLevel.OFFICIAL_PRIMARY,
        actionability_level=ActionabilityLevel.INFORMATIONAL,
        importance_score=0.75,
        urgency_score=0.60,
        data_mode=DataMode.LIVE,
        model_version="gemini-2.0-flash",
        prompt_version="1.0",
        schema_version="1.0",
        processing_run_id=run.id,
    )
    assert snap.data_mode == DataMode.LIVE

    # EventChange
    chg = EventChange(
        id=uuid.uuid4(),
        event_id=evt.id,
        to_snapshot_id=snap.id,
        change_type=ChangeType.ADDED,
        evidence_claim_ids=[str(clm.id)],
    )
    assert chg.change_type == ChangeType.ADDED

    # EventClaim
    e_clm = EventClaim(
        id=uuid.uuid4(),
        event_id=evt.id,
        snapshot_id=snap.id,
        claim_id=clm.id,
        role=EventClaimRole.PRIMARY,
    )
    assert e_clm.role == EventClaimRole.PRIMARY

    # EventMembershipAudit
    audit = EventMembershipAudit(
        id=uuid.uuid4(),
        article_version_id=ver.id,
        candidate_event_ids=[str(evt.id)],
        decision=ResolutionDecision.SAME_EVENT,
        deterministic_signals={"loc_match": True},
        decision_reason_codes=["LOC_MATCH"],
        evidence_claim_ids=[str(clm.id)],
        model_version="gemini-2.0-flash",
        prompt_version="1.0",
        schema_version="1.0",
        processing_run_id=run.id,
    )
    assert audit.decision == ResolutionDecision.SAME_EVENT

    # TimelineEntry
    tl = TimelineEntry(
        id=uuid.uuid4(),
        event_id=evt.id,
        snapshot_id=snap.id,
        event_time_precision=TimelinePrecision.EXACT,
        description="Gempa bumi terdeteksi oleh stasiun seismik.",
        evidence_claim_ids=[str(clm.id)],
        order_index=1,
    )
    assert tl.order_index == 1

    # Conflict
    conf = Conflict(
        id=uuid.uuid4(),
        event_id=evt.id,
        snapshot_id=snap.id,
        field_name="magnitude",
        claim_a_id=clm.id,
        claim_b_id=clm.id,
        value_a="5.0",
        value_b="5.2",
    )
    assert conf.field_name == "magnitude"

    # Action
    act = Action(
        id=uuid.uuid4(),
        event_id=evt.id,
        snapshot_id=snap.id,
        action_level=ActionabilityLevel.INFORMATIONAL,
        action_text="Masyarakat diimbau tetap tenang dan waspada gempa susulan.",
        source_type=ActionSourceType.OFFICIAL_EMERGENCY,
        evidence_claim_ids=[str(clm.id)],
    )
    assert act.source_type == ActionSourceType.OFFICIAL_EMERGENCY

    # ProcessingJob
    job = ProcessingJob(
        id=uuid.uuid4(),
        processing_run_id=run.id,
        job_type=JobType.EXTRACT,
        idempotency_key="key_123",
        status=JobStatus.QUEUED,
        correlation_id="corr_456",
        payload={"article_id": str(art.id)},
    )
    assert job.correlation_id == "corr_456"

    # EventRelation
    rel = EventRelation(
        id=uuid.uuid4(),
        from_event_id=evt.id,
        to_event_id=evt.id,
        relation_type=EventRelationType.RELATED_TO,
        confidence=0.88,
        processing_run_id=run.id,
    )
    assert rel.relation_type == EventRelationType.RELATED_TO
