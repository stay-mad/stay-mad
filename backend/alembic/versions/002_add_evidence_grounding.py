"""Add evidence grounding to event_snapshots

Revision ID: 002_add_evidence_grounding
Revises: 001_initial_schema
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_add_evidence_grounding"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # Add evidence_claim_ids and conflict_summary columns
    op.add_column(
        "event_snapshots",
        sa.Column(
            "what_happened_evidence_claim_ids",
            json_type,
            nullable=True,
            server_default="[]",
        ),
    )
    op.add_column(
        "event_snapshots",
        sa.Column(
            "why_it_matters_evidence_claim_ids",
            json_type,
            nullable=True,
            server_default="[]",
        ),
    )
    op.add_column(
        "event_snapshots",
        sa.Column(
            "who_is_affected_evidence_claim_ids",
            json_type,
            nullable=True,
            server_default="[]",
        ),
    )
    op.add_column(
        "event_snapshots",
        sa.Column("conflict_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "event_snapshots",
        sa.Column(
            "conflict_summary_evidence_claim_ids",
            json_type,
            nullable=True,
            server_default="[]",
        ),
    )

    # Create GIN indexes for efficient JSONB queries on PostgreSQL
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        op.create_index(
            "idx_snapshot_what_happened_evidence",
            "event_snapshots",
            ["what_happened_evidence_claim_ids"],
            postgresql_using="gin",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        op.drop_index(
            "idx_snapshot_what_happened_evidence", table_name="event_snapshots"
        )
    op.drop_column("event_snapshots", "conflict_summary_evidence_claim_ids")
    op.drop_column("event_snapshots", "conflict_summary")
    op.drop_column("event_snapshots", "who_is_affected_evidence_claim_ids")
    op.drop_column("event_snapshots", "why_it_matters_evidence_claim_ids")
    op.drop_column("event_snapshots", "what_happened_evidence_claim_ids")
