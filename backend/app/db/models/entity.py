from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, updated_at_col


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_entity_project_name"),
        # Exactly one primary brand per project.
        Index("uq_one_primary_brand", "project_id", unique=True, postgresql_where=text("is_primary_brand")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    competitor_type: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(2000))
    comparison_rationale: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(String)
    is_primary_brand: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
