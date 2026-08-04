"""projects, entities, diagnostic context versions, buying-group roles, audit log

Revision ID: 0002_projects_context
Revises: 0001_users
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_projects_context"
down_revision = "0001_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("market", sa.String(length=300), nullable=True),
        sa.Column("primary_language", sa.String(length=20), server_default=sa.text("'ar'"), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default=sa.text("'Africa/Cairo'"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("competitor_type", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("website_url", sa.String(length=2000), nullable=True),
        sa.Column("comparison_rationale", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("is_primary_brand", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_entity_project_name"),
        sa.CheckConstraint("entity_type in ('brand','competitor')", name="ck_entity_type"),
    )
    # Exactly one primary brand per project (partial unique index).
    op.create_index(
        "uq_one_primary_brand",
        "entities",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_primary_brand"),
    )

    op.create_table(
        "diagnostic_context_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("target_buying_decision", sa.String(), nullable=False),
        sa.Column("purchase_type", sa.String(length=40), nullable=False),
        sa.Column("primary_product_or_service", sa.String(), nullable=False),
        sa.Column("primary_segment_name", sa.String(length=300), nullable=False),
        sa.Column("primary_segment_definition", sa.String(), nullable=False),
        sa.Column("primary_decision_maker_role", sa.String(length=40), nullable=False),
        sa.Column("primary_decision_maker_label", sa.String(length=300), nullable=True),
        sa.Column("commercial_value_notes", sa.String(), nullable=True),
        sa.Column("commercial_value_amount", sa.Numeric(), nullable=True),
        sa.Column("commercial_value_currency", sa.String(length=3), nullable=True),
        sa.Column("primary_bottleneck", sa.String(length=20), nullable=False),
        sa.Column("bottleneck_statement", sa.String(), nullable=False),
        sa.Column("attention_score", sa.Integer(), nullable=True),
        sa.Column("attention_reasoning", sa.String(), nullable=True),
        sa.Column("desire_score", sa.Integer(), nullable=True),
        sa.Column("desire_reasoning", sa.String(), nullable=True),
        sa.Column("persuasion_score", sa.Integer(), nullable=True),
        sa.Column("persuasion_reasoning", sa.String(), nullable=True),
        sa.Column("friction_summary", sa.String(), nullable=True),
        sa.Column("score_evidence", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("analysis_period_start", sa.Date(), nullable=True),
        sa.Column("analysis_period_end", sa.Date(), nullable=True),
        sa.Column("comparison_period_start", sa.Date(), nullable=True),
        sa.Column("comparison_period_end", sa.Date(), nullable=True),
        sa.Column("included_channels", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "version_number", name="uq_context_project_version"),
        sa.CheckConstraint("attention_score is null or attention_score between 1 and 10", name="ck_attention_score"),
        sa.CheckConstraint("desire_score is null or desire_score between 1 and 10", name="ck_desire_score"),
        sa.CheckConstraint("persuasion_score is null or persuasion_score between 1 and 10", name="ck_persuasion_score"),
    )

    op.create_table(
        "buying_group_roles",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_role", sa.String(length=40), nullable=False),
        sa.Column("display_label", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("influence_level", sa.Integer(), nullable=True),
        sa.Column("success_definition", sa.String(), nullable=True),
        sa.Column("concerns", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_project", "audit_log", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_project", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("buying_group_roles")
    op.drop_table("diagnostic_context_versions")
    op.drop_index("uq_one_primary_brand", table_name="entities")
    op.drop_table("entities")
    op.drop_table("projects")
