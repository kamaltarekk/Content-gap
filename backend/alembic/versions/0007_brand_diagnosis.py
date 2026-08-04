"""brand_diagnoses, brand_readiness_scores, brand_findings

Revision ID: 0007_brand_diagnosis
Revises: 0006_voc_claims_performance
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_brand_diagnosis"
down_revision = "0006_voc_claims_performance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_diagnoses",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "context_version_id",
            sa.Uuid(),
            sa.ForeignKey("diagnostic_context_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("readiness_grade", sa.String(length=1), nullable=True),
        sa.Column("primary_bottleneck", sa.String(length=20), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("limitations", sa.String(), server_default=sa.text("''"), nullable=False),
        sa.Column("audits", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_brand_diag_project", "brand_diagnoses", ["project_id"])

    op.create_table(
        "brand_readiness_scores",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "diagnosis_id", sa.Uuid(), sa.ForeignKey("brand_diagnoses.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=30), server_default=sa.text("'low'"), nullable=False),
        sa.Column("rationale", sa.String(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "evidence_span_id", sa.Uuid(), sa.ForeignKey("evidence_spans.id", ondelete="SET NULL"), nullable=True
        ),
        sa.CheckConstraint("score between 0 and 10", name="ck_readiness_score_range"),
    )

    op.create_table(
        "brand_findings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "diagnosis_id", sa.Uuid(), sa.ForeignKey("brand_diagnoses.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.String(length=30), nullable=False),
        sa.Column("finding_status", sa.String(length=20), server_default=sa.text("'inference'"), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("limitations", sa.String(), nullable=True),
        sa.Column("is_non_content_blocker", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("evidence_span_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_brand_finding_diag", "brand_findings", ["diagnosis_id"])


def downgrade() -> None:
    op.drop_index("ix_brand_finding_diag", table_name="brand_findings")
    op.drop_table("brand_findings")
    op.drop_table("brand_readiness_scores")
    op.drop_index("ix_brand_diag_project", table_name="brand_diagnoses")
    op.drop_table("brand_diagnoses")
