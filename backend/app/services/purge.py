"""Project purge (spec §25.4, §25.6, §31.5).

Soft-delete (a 7-day recovery window) already lives on the projects DELETE endpoint. This is the
explicit hard purge: because every table hangs off ``projects.id`` with ``ON DELETE CASCADE``,
purging is a single delete of the project row that removes all raw and derived data. Returns
pre-purge counts for the audit trail — counts only, never evidence text.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content_piece import ContentPiece
from app.db.models.project import Project
from app.db.models.source import Source


class PurgeError(Exception):
    pass


async def purge_project(session: AsyncSession, project_id: uuid.UUID) -> dict:
    project = await session.get(Project, project_id)
    if project is None:
        raise PurgeError("project_not_found")

    source_count = (
        await session.execute(select(func.count()).select_from(Source).where(Source.project_id == project_id))
    ).scalar_one()
    piece_count = (
        await session.execute(
            select(func.count()).select_from(ContentPiece).where(ContentPiece.project_id == project_id)
        )
    ).scalar_one()

    # Cascade delete removes sources, snapshots, pieces, spans, classifications, voc, claims,
    # performance, diagnoses, gaps, reports, cost ledger — everything keyed on projects.id.
    await session.execute(delete(Project).where(Project.id == project_id))
    await session.flush()
    return {"purged_project_id": str(project_id), "sources": int(source_count), "content_pieces": int(piece_count)}
