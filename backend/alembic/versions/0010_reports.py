"""reports

Revision ID: 0010_reports
Revises: 0009_gap_engine
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010_reports"
down_revision = "0009_gap_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("readiness_status", sa.String(length=40), nullable=False),
        sa.Column("readiness_reason", sa.String(), server_default=sa.text("''"), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("version_manifest", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_report_project", "reports", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_report_project", table_name="reports")
    op.drop_table("reports")
