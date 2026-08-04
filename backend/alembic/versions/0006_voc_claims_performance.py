"""voc_entries, claims, claim_evidence, performance_records

Revision ID: 0006_voc_claims_performance
Revises: 0005_classifications
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_voc_claims_performance"
down_revision = "0005_classifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voc_entries",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "content_piece_id", sa.Uuid(), sa.ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "evidence_span_id", sa.Uuid(), sa.ForeignKey("evidence_spans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("bank_type", sa.String(length=30), nullable=False),
        sa.Column("verbatim_phrase", sa.String(), nullable=False),
        sa.Column("pattern_key", sa.String(length=64), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("confidence", sa.String(length=30), server_default=sa.text("'low'"), nullable=False),
        sa.Column("review_status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_voc_project_pattern", "voc_entries", ["project_id", "pattern_key"])

    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "content_piece_id", sa.Uuid(), sa.ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("claim_text", sa.String(), nullable=False),
        sa.Column("claim_type", sa.String(length=30), nullable=False),
        sa.Column("proof_status", sa.String(length=30), server_default=sa.text("'unsupported'"), nullable=False),
        sa.Column("confidence", sa.String(length=30), server_default=sa.text("'low'"), nullable=False),
        sa.Column("finding_status", sa.String(length=20), server_default=sa.text("'brand_claim'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "claim_evidence",
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "evidence_span_id",
            sa.Uuid(),
            sa.ForeignKey("evidence_spans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("proof_type", sa.String(length=40), nullable=False),
        sa.Column("evidence_role", sa.String(length=30), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.CheckConstraint("quality_score is null or quality_score between 0 and 10", name="ck_claim_ev_quality"),
    )

    op.create_table(
        "performance_records",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_piece_id", sa.Uuid(), sa.ForeignKey("content_pieces.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Numeric(), nullable=False),
        sa.Column("metric_unit", sa.String(length=50), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("paid_organic_status", sa.String(length=20), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("spend", sa.Numeric(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("audience_size", sa.Numeric(), nullable=True),
        sa.Column("metric_definition", sa.String(), nullable=True),
        sa.Column("is_proxy", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("performance_records")
    op.drop_table("claim_evidence")
    op.drop_table("claims")
    op.drop_index("ix_voc_project_pattern", table_name="voc_entries")
    op.drop_table("voc_entries")
