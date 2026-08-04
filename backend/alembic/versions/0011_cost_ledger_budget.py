"""cost_ledger + projects.budget_cap_usd

Revision ID: 0011_cost_ledger_budget
Revises: 0010_reports
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011_cost_ledger_budget"
down_revision = "0010_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("budget_cap_usd", sa.Numeric(), nullable=True))
    op.create_table(
        "cost_ledger",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("task", sa.String(length=60), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_usd", sa.Numeric(), server_default=sa.text("0"), nullable=False),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cost_ledger_project", "cost_ledger", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_cost_ledger_project", table_name="cost_ledger")
    op.drop_table("cost_ledger")
    op.drop_column("projects", "budget_cap_usd")
