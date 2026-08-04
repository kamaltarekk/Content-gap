"""competitor_collections, competitor_collection_items, competitor_diagnoses, competitor_findings

Revision ID: 0008_competitor_diagnosis
Revises: 0007_brand_diagnosis
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_competitor_diagnosis"
down_revision = "0007_brand_diagnosis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competitor_collections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'empty'"), nullable=False),
        sa.Column("requested_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("collected_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("blocked_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("duplicate_rate", sa.Numeric(), server_default=sa.text("0"), nullable=False),
        sa.Column("channels", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_comp_collection_entity", "competitor_collections", ["entity_id"])

    op.create_table(
        "competitor_collection_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Uuid(),
            sa.ForeignKey("competitor_collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("item_status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "content_piece_id", sa.Uuid(), sa.ForeignKey("content_pieces.id", ondelete="SET NULL"), nullable=True
        ),
    )

    op.create_table(
        "competitor_diagnoses",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "collection_id",
            sa.Uuid(),
            sa.ForeignKey("competitor_collections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sample_sufficiency",
            sa.String(length=30),
            server_default=sa.text("'insufficient_evidence'"),
            nullable=False,
        ),
        sa.Column("sample_piece_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("limitation_banner", sa.String(), server_default=sa.text("''"), nullable=False),
        sa.Column("audits", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_comp_diag_project", "competitor_diagnoses", ["project_id"])

    op.create_table(
        "competitor_findings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "diagnosis_id",
            sa.Uuid(),
            sa.ForeignKey("competitor_diagnoses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("presence", sa.String(length=30), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("finding_status", sa.String(length=20), server_default=sa.text("'inference'"), nullable=False),
        sa.Column("confidence", sa.String(length=30), server_default=sa.text("'low'"), nullable=False),
        sa.Column("is_public_proxy", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("evidence_span_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_comp_finding_diag", "competitor_findings", ["diagnosis_id"])


def downgrade() -> None:
    op.drop_index("ix_comp_finding_diag", table_name="competitor_findings")
    op.drop_table("competitor_findings")
    op.drop_index("ix_comp_diag_project", table_name="competitor_diagnoses")
    op.drop_table("competitor_diagnoses")
    op.drop_table("competitor_collection_items")
    op.drop_index("ix_comp_collection_entity", table_name="competitor_collections")
    op.drop_table("competitor_collections")
