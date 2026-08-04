from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class Report(Base):
    """An immutable diagnostic report snapshot. Once written, ``snapshot`` and ``version_manifest``
    are never mutated — adding data or changing weights creates a NEW report so prior reports stay
    reproducible with a complete evidence + version trace (spec §6.2, §12.13). The report is a
    diagnosis: it carries a strategy-readiness decision but no strategy or content calendar."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'draft'"))
    readiness_status: Mapped[str] = mapped_column(String(40), nullable=False)
    readiness_reason: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)  # frozen at generation time
    version_manifest: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_col()
    approved_by: Mapped[uuid.UUID | None] = mapped_column()
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
