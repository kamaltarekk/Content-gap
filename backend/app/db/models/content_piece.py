from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, updated_at_col


class ContentPiece(Base):
    __tablename__ = "content_pieces"
    __table_args__ = (
        Index("ix_content_project_entity", "project_id", "entity_id"),
        Index("ix_content_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(300))
    content_format: Mapped[str] = mapped_column(String(40), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(100))
    published_at: Mapped[datetime | None] = mapped_column()
    title: Mapped[str | None] = mapped_column(String(1000))
    original_text: Mapped[str] = mapped_column(String, nullable=False)
    normalized_text: Mapped[str] = mapped_column(String, nullable=False)
    language_code: Mapped[str] = mapped_column(String(20), nullable=False)
    original_location: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    duplicate_group_id: Mapped[uuid.UUID | None] = mapped_column()
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    include_in_analysis: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class EvidenceSpan(Base):
    __tablename__ = "evidence_spans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    content_piece_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
    )
    span_type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    quoted_text: Mapped[str] = mapped_column(String, nullable=False)
    source_location: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    language_code: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_origin: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = created_at_col()
