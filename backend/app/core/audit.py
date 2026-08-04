from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    object_type: str,
    object_id: str,
    project_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            action=action,
            object_type=object_type,
            object_id=object_id,
            project_id=project_id,
            user_id=user_id,
            metadata_json=metadata or {},
        )
    )
