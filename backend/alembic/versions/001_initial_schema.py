"""Initial schema migration: 16 canonical entities and pgvector.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-12
Authority: docs/architecture/B-data-model.md, ADR-003, ADR-007
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Dual-dialect JSON type for migration flexibility
json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 0. Enable pgvector extension if PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("RSS", "API", "OFFICIAL_GOV", "SCRAPE", name="source_type_enum"),
            nullable=False,
        ),
        sa.Column(
            "source_tier",
            sa.Enum("TIER_1", "TIER_2", name="source_tier_enum"),
            nullable=False,
        ),
        sa.Column("source_family", sa.String(100), nullable=False),
        sa.Column("robots_policy", sa.Text(), nullable=True),
        sa.Column(
            "rate_limit_per_min", sa.Integer(), nullable=False, server_default="20"
        ),
        sa.Column("retention_rule", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 2. Articles table
    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "DISASTER_AND_WEATHER",
                "TRANSPORTATION_AND_INFRASTRUCTURE",
                "GOVERNMENT_AND_PUBLIC_POLICY",
                name="event_category_enum",
            ),
            nullable=False,
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="id"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_article_content_hash", "articles", ["content_hash"], unique=True
    )

    # 3. Processing Runs table
    op.create_table(
        "processing_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "stage",
            sa.Enum(
                "INGEST",
                "EXTRACT",
                "RESOLVE",
                "SYNTHESIZE",
                "EVALUATE",
                name="processing_stage_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "DEAD_LETTER",
                name="run_status_enum",
            ),
            nullable=False,
            server_default="RUNNING",
        ),
        sa.Column(
            "articles_processed", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("cost_estimate_usd", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 4. Article Versions table
    op.create_table(
        "article_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "article_id",
            sa.Uuid(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fetch_time",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("published_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("full_text_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "schema_version", sa.String(50), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "processing_run_id",
            sa.Uuid(),
            sa.ForeignKey("processing_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 5. Locations table
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("district", sa.String(255), nullable=True),
        sa.Column("province", sa.String(255), nullable=True),
        sa.Column(
            "country", sa.String(100), nullable=False, server_default="Indonesia"
        ),
        sa.Column("continent", sa.String(100), nullable=True),
        sa.Column(
            "geo_level",
            sa.Enum(
                "CITY",
                "PROVINCE",
                "COUNTRY",
                "CONTINENT",
                "WORLD",
                name="geo_level_enum",
            ),
            nullable=False,
        ),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 6. Claims table
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "article_version_id",
            sa.Uuid(),
            sa.ForeignKey("article_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_span", sa.String(200), nullable=False),
        sa.Column("speaker", sa.String(255), nullable=True),
        sa.Column("negation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("location_raw", sa.String(255), nullable=True),
        sa.Column("event_time_raw", sa.String(255), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "event_time_precision",
            sa.Enum(
                "EXACT",
                "APPROXIMATE",
                "DAY",
                "RANGE",
                "UNKNOWN",
                name="timeline_precision_enum",
            ),
            nullable=False,
        ),
        sa.Column("event_time_qualifier", sa.String(100), nullable=True),
        sa.Column("source_timezone", sa.String(50), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="id"),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column(
            "processing_run_id",
            sa.Uuid(),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_claim_event_time", "claims", ["event_time"])
    op.create_index("idx_processing_run_id", "claims", ["processing_run_id"])

    # 7. Events table
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "DISASTER_AND_WEATHER",
                "TRANSPORTATION_AND_INFRASTRUCTURE",
                "GOVERNMENT_AND_PUBLIC_POLICY",
                name="event_category_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "primary_location_id",
            sa.Uuid(),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_event_category", "events", ["category"])
    op.create_index(
        "idx_event_location", "events", ["primary_location_id", "time_window_start"]
    )

    # 8. Event Snapshots table
    op.create_table(
        "event_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("what_happened", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("who_is_affected", sa.Text(), nullable=True),
        sa.Column("what_is_unknown", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column(
            "confidence_bucket",
            sa.Enum("HIGH", "MEDIUM", "LOW", name="confidence_bucket_enum"),
            nullable=False,
        ),
        sa.Column(
            "evidence_status",
            sa.Enum(
                "SUPPORTED",
                "CONFLICTING",
                "INSUFFICIENT",
                "RETRACTED",
                name="evidence_status_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "verification_level",
            sa.Enum(
                "OFFICIAL_PRIMARY",
                "INDEPENDENTLY_CORROBORATED",
                "SINGLE_SOURCE",
                name="verification_level_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "actionability_level",
            sa.Enum(
                "ACTION_REQUIRED",
                "ACTION_RECOMMENDED",
                "OPTIONAL",
                "INFORMATIONAL",
                "NO_IMMEDIATE_ACTION",
                name="actionability_level_enum",
            ),
            nullable=False,
        ),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("urgency_score", sa.Float(), nullable=False),
        sa.Column(
            "data_mode",
            sa.Enum("LIVE", "DEMO", "DEGRADED", name="data_mode_enum"),
            nullable=False,
            server_default="LIVE",
        ),
        sa.Column(
            "last_processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column(
            "processing_run_id",
            sa.Uuid(),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_processing_run_id_snapshot", "event_snapshots", ["processing_run_id"]
    )

    # 9. Event Changes table
    op.create_table(
        "event_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "from_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("event_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "to_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("event_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "change_type",
            sa.Enum(
                "ADDED", "UPDATED", "CORRECTED", "RETRACTED", name="change_type_enum"
            ),
            nullable=False,
        ),
        sa.Column(
            "change_category",
            sa.Enum(
                "AREA_CHANGE",
                "ALERT_STATUS",
                "ESCALATION",
                "NUMERICAL",
                "NEWLY_CONFIRMED",
                "NEWLY_CONFLICTING",
                name="change_category_enum",
            ),
            nullable=True,
        ),
        sa.Column("field_name", sa.String(255), nullable=True),
        sa.Column("before_value", sa.Text(), nullable=True),
        sa.Column("after_value", sa.Text(), nullable=True),
        sa.Column("evidence_claim_ids", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 10. Event Claims table
    op.create_table(
        "event_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("event_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "claim_id",
            sa.Uuid(),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "PRIMARY",
                "SUPPORTING",
                "CONFLICTING",
                "RETRACTED",
                name="event_claim_role_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 11. Event Membership Audits table
    op.create_table(
        "event_membership_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "article_version_id",
            sa.Uuid(),
            sa.ForeignKey("article_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("candidate_event_ids", json_type, nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "SAME_EVENT",
                "RELATED_EVENT",
                "SEPARATE_EVENT",
                "NEEDS_REVIEW",
                name="resolution_decision_enum",
            ),
            nullable=False,
        ),
        sa.Column("deterministic_signals", json_type, nullable=False),
        sa.Column("decision_reason_codes", json_type, nullable=False),
        sa.Column("evidence_claim_ids", json_type, nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column(
            "processing_run_id",
            sa.Uuid(),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 12. Timeline Entries table
    op.create_table(
        "timeline_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("event_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "event_time_precision",
            sa.Enum(
                "EXACT",
                "APPROXIMATE",
                "DAY",
                "RANGE",
                "UNKNOWN",
                name="timeline_precision_enum",
            ),
            nullable=False,
        ),
        sa.Column("event_time_qualifier", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_claim_ids", json_type, nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 13. Conflicts table
    op.create_table(
        "conflicts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("event_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(255), nullable=False),
        sa.Column(
            "claim_a_id",
            sa.Uuid(),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_b_id",
            sa.Uuid(),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value_a", sa.Text(), nullable=False),
        sa.Column("value_b", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "resolution_claim_id",
            sa.Uuid(),
            sa.ForeignKey("claims.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 14. Actions table
    op.create_table(
        "actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("event_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "action_level",
            sa.Enum(
                "ACTION_REQUIRED",
                "ACTION_RECOMMENDED",
                "OPTIONAL",
                "INFORMATIONAL",
                "NO_IMMEDIATE_ACTION",
                name="actionability_level_enum",
            ),
            nullable=False,
        ),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "OFFICIAL_EMERGENCY",
                "OFFICIAL_GOV",
                "OFFICIAL_HEALTH",
                "INFORMATIONAL",
                name="action_source_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("evidence_claim_ids", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 15. Processing Jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "processing_run_id",
            sa.Uuid(),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_type",
            sa.Enum("INGEST", "EXTRACT", "RESOLVE", "SYNTHESIZE", name="job_type_enum"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "DONE",
                "FAILED",
                "DEAD_LETTER",
                name="job_status_enum",
            ),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column(
            "enqueued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("idx_job_idempotency_key", "processing_jobs", ["idempotency_key"])
    op.create_index("idx_job_correlation_id", "processing_jobs", ["correlation_id"])

    # 16. Event Relations table
    op.create_table(
        "event_relations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "from_event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "relation_type",
            sa.Enum("RELATED_TO", name="event_relation_type_enum"),
            nullable=False,
            server_default="RELATED_TO",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "processing_run_id",
            sa.Uuid(),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("event_relations")
    op.drop_table("processing_jobs")
    op.drop_table("actions")
    op.drop_table("conflicts")
    op.drop_table("timeline_entries")
    op.drop_table("event_membership_audits")
    op.drop_table("event_claims")
    op.drop_table("event_changes")
    op.drop_table("event_snapshots")
    op.drop_table("events")
    op.drop_table("claims")
    op.drop_table("locations")
    op.drop_table("article_versions")
    op.drop_table("processing_runs")
    op.drop_table("articles")
    op.drop_table("sources")
