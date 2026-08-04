"""gap_analysis_runs, coverage_cells, gaps

Revision ID: 0009_gap_engine
Revises: 0008_competitor_diagnosis
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009_gap_engine"
down_revision = "0008_competitor_diagnosis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gap_analysis_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_version", sa.String(length=30), server_default=sa.text("'v0'"), nullable=False),
        sa.Column("primary_bottleneck", sa.String(length=20), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("weights", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_gap_run_project", "gap_analysis_runs", ["project_id"])

    op.create_table(
        "coverage_cells",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("gap_analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_brand", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("territory", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("presence", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("relevance", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("depth", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("proof", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("touchpoint", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("micro_decision", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reasoning", sa.String(), server_default=sa.text("''"), nullable=False),
        sa.Column("evidence_span_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.create_index("ix_coverage_cell_run", "coverage_cells", ["run_id"])

    op.create_table(
        "gaps",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("gap_analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("territory", sa.String(length=40), nullable=False),
        sa.Column("gap_type", sa.String(length=40), nullable=False),
        sa.Column("gap_status", sa.String(length=30), nullable=False),
        sa.Column("severity_label", sa.String(length=20), nullable=False),
        sa.Column("severity_score", sa.Numeric(), nullable=False),
        sa.Column("confidence_label", sa.String(length=30), nullable=False),
        sa.Column("confidence_score", sa.Numeric(), nullable=False),
        sa.Column("root_cause_type", sa.String(length=30), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("brand_score", sa.Integer(), nullable=True),
        sa.Column("best_competitor_score", sa.Integer(), nullable=True),
        sa.Column("evidence_span_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column(
            "alternative_explanations", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("competitor_only_signal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("requires_human_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_gap_run", "gaps", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_gap_run", table_name="gaps")
    op.drop_table("gaps")
    op.drop_index("ix_coverage_cell_run", table_name="coverage_cells")
    op.drop_table("coverage_cells")
    op.drop_index("ix_gap_run_project", table_name="gap_analysis_runs")
    op.drop_table("gap_analysis_runs")
