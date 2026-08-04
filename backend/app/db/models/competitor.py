from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class CompetitorCollection(Base):
    """A record of a public/uploaded sample gathered for one competitor. The manifest is honest
    about what was and was not collected — blocked or failed URLs make the status ``partial`` and
    are never silently dropped (spec §15, §16.4)."""

    __tablename__ = "competitor_collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'empty'"))
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    collected_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    duplicate_rate: Mapped[float] = mapped_column(Numeric, nullable=False, server_default=text("0"))
    channels: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_col()


class CompetitorCollectionItem(Base):
    """One collected/blocked/failed item in a competitor sample. Blocked and failed URLs are kept so
    partial collection is visible rather than hidden."""

    __tablename__ = "competitor_collection_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitor_collections.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str | None] = mapped_column(String(2000))
    item_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String)
    content_piece_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("content_pieces.id", ondelete="SET NULL"))


class CompetitorDiagnosis(Base):
    """An observable-only competitor diagnosis. Carries the mandatory public-evidence limitation
    banner (spec §15.1) and the computed sample sufficiency. Serialized audits back the UI."""

    __tablename__ = "competitor_diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("competitor_collections.id", ondelete="SET NULL")
    )
    sample_sufficiency: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'insufficient_evidence'")
    )
    sample_piece_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    limitation_banner: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    audits: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_col()


class CompetitorFinding(Base):
    """An observable competitor finding. ``finding_status`` is never ``observed_fact`` unless the
    competitor explicitly states it; audience/positioning defaults to inference/hypothesis
    (spec §15.3). ``presence`` distinguishes 'found' from 'not_found_in_sample' so absence is never
    written as 'the competitor does not do X' (spec §6.3)."""

    __tablename__ = "competitor_findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitor_diagnoses.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    presence: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'unknown'"))
    finding_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'inference'"))
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'low'"))
    is_public_proxy: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    summary: Mapped[str] = mapped_column(String, nullable=False)
    evidence_span_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = created_at_col()
