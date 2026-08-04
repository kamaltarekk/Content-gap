from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class DiagnosticContextVersion(Base):
    __tablename__ = "diagnostic_context_versions"
    __table_args__ = (UniqueConstraint("project_id", "version_number", name="uq_context_project_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    target_buying_decision: Mapped[str] = mapped_column(String, nullable=False)
    purchase_type: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_product_or_service: Mapped[str] = mapped_column(String, nullable=False)
    primary_segment_name: Mapped[str] = mapped_column(String(300), nullable=False)
    primary_segment_definition: Mapped[str] = mapped_column(String, nullable=False)
    primary_decision_maker_role: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_decision_maker_label: Mapped[str | None] = mapped_column(String(300))

    commercial_value_notes: Mapped[str | None] = mapped_column(String)
    commercial_value_amount: Mapped[float | None] = mapped_column(Numeric)
    commercial_value_currency: Mapped[str | None] = mapped_column(String(3))

    primary_bottleneck: Mapped[str] = mapped_column(String(20), nullable=False)
    bottleneck_statement: Mapped[str] = mapped_column(String, nullable=False)

    attention_score: Mapped[int | None] = mapped_column(Integer)
    attention_reasoning: Mapped[str | None] = mapped_column(String)
    desire_score: Mapped[int | None] = mapped_column(Integer)
    desire_reasoning: Mapped[str | None] = mapped_column(String)
    persuasion_score: Mapped[int | None] = mapped_column(Integer)
    persuasion_reasoning: Mapped[str | None] = mapped_column(String)
    friction_summary: Mapped[str | None] = mapped_column(String)

    # Evidence references supporting A/D/P scores (spec §8.1). Until the evidence system exists
    # (Phase 3) these are opaque reference strings; validated by count when a score is entered.
    score_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    analysis_period_start: Mapped[date | None] = mapped_column(Date)
    analysis_period_end: Mapped[date | None] = mapped_column(Date)
    comparison_period_start: Mapped[date | None] = mapped_column(Date)
    comparison_period_end: Mapped[date | None] = mapped_column(Date)
    included_channels: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    created_by: Mapped[uuid.UUID | None] = mapped_column()
    approved_by: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = created_at_col()
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
