"""users table + required extensions

Revision ID: 0001_users
Revises:
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("users")
