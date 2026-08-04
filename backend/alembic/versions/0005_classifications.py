"""content_classifications

Revision ID: 0005_classifications
Revises: 0004_jobs
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_classifications"
down_revision = "0004_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_classifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "content_piece_id",
            sa.Uuid(),
            sa.ForeignKey("content_pieces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
        sa.Column("classification_dimension", sa.String(length=60), nullable=False),
        sa.Column("proposed_value", sa.String(), nullable=True),
        sa.Column("approved_value", sa.String(), nullable=True),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.String(length=30), nullable=False),
        sa.Column("reasoning", sa.String(), nullable=True),
        sa.Column("evidence_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("review_status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_classification_piece", "content_classifications", ["content_piece_id"])
    op.create_index("ix_classification_fingerprint", "content_classifications", ["fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_classification_fingerprint", table_name="content_classifications")
    op.drop_index("ix_classification_piece", table_name="content_classifications")
    op.drop_table("content_classifications")
