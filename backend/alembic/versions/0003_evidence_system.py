"""sources, source snapshots, content pieces, evidence spans

Revision ID: 0003_evidence_system
Revises: 0002_projects_context
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_evidence_system"
down_revision = "0002_projects_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_category", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("original_url", sa.String(length=2000), nullable=True),
        sa.Column("original_filename", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_number", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("final_url", sa.String(length=2000), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=200), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.Column("normalized_text_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_object_key", sa.String(length=1000), nullable=True),
        sa.Column("extracted_text_object_key", sa.String(length=1000), nullable=True),
        sa.Column("parser_name", sa.String(length=100), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=True),
        sa.Column("extraction_quality", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_id", "snapshot_number", name="uq_snapshot_number"),
        sa.UniqueConstraint("source_id", "raw_sha256", name="uq_snapshot_raw_hash"),
    )

    op.create_table(
        "content_pieces",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "source_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("source_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=300), nullable=True),
        sa.Column("content_format", sa.String(length=40), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(length=1000), nullable=True),
        sa.Column("original_text", sa.String(), nullable=False),
        sa.Column("normalized_text", sa.String(), nullable=False),
        sa.Column("language_code", sa.String(length=20), nullable=False),
        sa.Column("original_location", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("duplicate_group_id", sa.Uuid(), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("include_in_analysis", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_content_project_entity", "content_pieces", ["project_id", "entity_id"])
    op.create_index("ix_content_hash", "content_pieces", ["content_hash"])

    op.create_table(
        "evidence_spans",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "content_piece_id",
            sa.Uuid(),
            sa.ForeignKey("content_pieces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("span_type", sa.String(length=100), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("quoted_text", sa.String(), nullable=False),
        sa.Column("source_location", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("language_code", sa.String(length=20), nullable=False),
        sa.Column("created_by_origin", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "start_offset is null or end_offset is null or start_offset <= end_offset",
            name="ck_span_offsets",
        ),
    )
    op.create_index("ix_evidence_piece", "evidence_spans", ["content_piece_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_piece", table_name="evidence_spans")
    op.drop_table("evidence_spans")
    op.drop_index("ix_content_hash", table_name="content_pieces")
    op.drop_index("ix_content_project_entity", table_name="content_pieces")
    op.drop_table("content_pieces")
    op.drop_table("source_snapshots")
    op.drop_table("sources")
