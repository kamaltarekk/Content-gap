from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, updated_at_col


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String(300))
    primary_language: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'ar'"))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'Africa/Cairo'"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'active'"))
    created_by: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
