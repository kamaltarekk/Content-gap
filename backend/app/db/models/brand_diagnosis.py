from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class BrandDiagnosis(Base):
    """One evidence-verified brand diagnosis run. Holds the readiness grade, global limitations,
    and a serialized snapshot of every audit (scorecard, sales elements, journey, decision
    alignment, claim/proof, performance) for the UI. It never stores strategy or recommendations."""

    __tablename__ = "brand_diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    context_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diagnostic_context_versions.id", ondelete="SET NULL")
    )
    readiness_grade: Mapped[str | None] = mapped_column(String(1))
    primary_bottleneck: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'unknown'"))
    limitations: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    audits: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_col()


class BrandReadinessScore(Base):
    """A single readiness dimension score (0–10) with its rationale and cited evidence span.
    Dimension scores are always shown before any A–D grade (spec §16.5)."""

    __tablename__ = "brand_readiness_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_diagnoses.id", ondelete="CASCADE"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'low'"))
    rationale: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    evidence_span_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_spans.id", ondelete="SET NULL"))


class BrandFinding(Base):
    """An evidence-anchored observation. Severity and confidence are stored in SEPARATE columns and
    must never be collapsed (spec §4.19). Findings describe what the evidence shows — never a
    recommendation. ``evidence_span_ids`` holds only real span ids so the UI can link each finding
    to its verbatim source."""

    __tablename__ = "brand_findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_diagnoses.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20))  # separate from confidence, may be null
    confidence: Mapped[str] = mapped_column(String(30), nullable=False)
    finding_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'inference'"))
    summary: Mapped[str] = mapped_column(String, nullable=False)
    limitations: Mapped[str | None] = mapped_column(String)
    is_non_content_blocker: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    evidence_span_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = created_at_col()
