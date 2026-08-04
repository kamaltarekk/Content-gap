from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, updated_at_col


class VocEntry(Base):
    __tablename__ = "voc_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    content_piece_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
    )
    evidence_span_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_spans.id", ondelete="CASCADE"), nullable=False
    )
    bank_type: Mapped[str] = mapped_column(String(30), nullable=False)
    verbatim_phrase: Mapped[str] = mapped_column(String, nullable=False)  # stored EXACTLY, never rewritten
    pattern_key: Mapped[str | None] = mapped_column(String(64))
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'low'"))
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    created_at: Mapped[datetime] = created_at_col()


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    content_piece_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(String, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(30), nullable=False)
    proof_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'unsupported'"))
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'low'"))
    finding_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'brand_claim'"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True)
    evidence_span_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_spans.id", ondelete="CASCADE"), primary_key=True
    )
    proof_type: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(30), nullable=False)
    quality_score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String)


class PerformanceRecord(Base):
    __tablename__ = "performance_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    content_piece_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("content_pieces.id", ondelete="SET NULL"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    metric_unit: Mapped[str | None] = mapped_column(String(50))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(100))
    paid_organic_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'unknown'"))
    spend: Mapped[float | None] = mapped_column(Numeric)
    currency: Mapped[str | None] = mapped_column(String(3))
    audience_size: Mapped[float | None] = mapped_column(Numeric)
    metric_definition: Mapped[str | None] = mapped_column(String)
    is_proxy: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created_at_col()
