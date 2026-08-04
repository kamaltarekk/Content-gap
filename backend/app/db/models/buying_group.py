from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col


class BuyingGroupRole(Base):
    __tablename__ = "buying_group_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    canonical_role: Mapped[str] = mapped_column(String(40), nullable=False)
    display_label: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    influence_level: Mapped[int | None] = mapped_column(Integer)
    success_definition: Mapped[str | None] = mapped_column(String)
    concerns: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_col()
