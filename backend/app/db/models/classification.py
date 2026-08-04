from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class ContentClassification(Base):
    """One row per (content piece × dimension × attempt). The AI proposal and the human decision
    are stored SEPARATELY (spec §6.27): a human edit sets ``approved_value`` and never overwrites
    ``proposed_value``. History is preserved by keeping old rows (``is_current=false``).
    """

    __tablename__ = "content_classifications"
    __table_args__ = (
        Index("ix_classification_piece", "content_piece_id"),
        Index("ix_classification_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    content_piece_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_pieces.id", ondelete="CASCADE"), nullable=False
    )
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column()
    classification_dimension: Mapped[str] = mapped_column(String(60), nullable=False)
    proposed_value: Mapped[str | None] = mapped_column(String)
    approved_value: Mapped[str | None] = mapped_column(String)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(30), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(String)
    evidence_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column()
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = created_at_col()
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
