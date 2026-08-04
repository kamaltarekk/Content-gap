from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class GapAnalysisRun(Base):
    """One comparative coverage + gap-detection run. The ``rule_version`` and weights are pinned so
    prior reports stay reproducible when methodology changes (spec §16, §6.2)."""

    __tablename__ = "gap_analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'v0'"))
    primary_bottleneck: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'unknown'"))
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_col()


class CoverageCell(Base):
    """Coverage of one entity for one territory (sales element), scored 0–10 from the six components
    in spec §16.1. Every cell keeps its evidence spans and a reasoning string (§16.2)."""

    __tablename__ = "coverage_cells"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gap_analysis_runs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    is_brand: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    territory: Mapped[str] = mapped_column(String(40), nullable=False)  # a sales element
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    presence: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    relevance: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    depth: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    proof: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    touchpoint: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    micro_decision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    reasoning: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    evidence_span_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class Gap(Base):
    """A detected gap. Severity and confidence are stored as separate scores AND labels and never
    collapsed (spec §18). The engine never emits ``confirmed`` — a critical gap can only become
    confirmed through explicit human approval (§18.3). High/critical gaps carry at least one
    alternative explanation the reviewer must accept or reject (§18.4)."""

    __tablename__ = "gaps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gap_analysis_runs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    territory: Mapped[str] = mapped_column(String(40), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(40), nullable=False)
    gap_status: Mapped[str] = mapped_column(String(30), nullable=False)
    severity_label: Mapped[str] = mapped_column(String(20), nullable=False)
    severity_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    root_cause_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'unknown'"))
    summary: Mapped[str] = mapped_column(String, nullable=False)
    brand_score: Mapped[int | None] = mapped_column(Integer)
    best_competitor_score: Mapped[int | None] = mapped_column(Integer)
    evidence_span_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    alternative_explanations: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    competitor_only_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column()
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
