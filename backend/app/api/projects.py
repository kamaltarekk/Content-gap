from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.audit import write_audit
from app.core.enums import LanguageCode
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.project import Project
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    market: str | None = None
    primary_language: LanguageCode = LanguageCode.ar
    timezone: str = "Africa/Cairo"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    market: str | None = None
    primary_language: LanguageCode | None = None
    timezone: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    market: str | None
    primary_language: str
    timezone: str
    status: str


def _out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        description=p.description,
        market=p.market,
        primary_language=p.primary_language,
        timezone=p.timezone,
        status=p.status,
    )


async def _get_active(session: AsyncSession, project_id: uuid.UUID) -> Project:
    p = await session.get(Project, project_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project_not_found")
    return p


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectOut:
    p = Project(
        name=body.name,
        description=body.description,
        market=body.market,
        primary_language=body.primary_language.value,
        timezone=body.timezone,
        created_by=user.id,
    )
    session.add(p)
    await session.flush()
    await write_audit(
        session, action="create", object_type="project", object_id=str(p.id), project_id=p.id, user_id=user.id
    )
    await session.commit()
    await session.refresh(p)
    return _out(p)


@router.get("", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)) -> list[ProjectOut]:
    rows = (
        (await session.execute(select(Project).where(Project.deleted_at.is_(None)).order_by(Project.created_at.desc())))
        .scalars()
        .all()
    )
    return [_out(p) for p in rows]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> ProjectOut:
    return _out(await _get_active(session, project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectOut:
    p = await _get_active(session, project_id)
    data = body.model_dump(exclude_unset=True)
    if "primary_language" in data and data["primary_language"] is not None:
        data["primary_language"] = (
            data["primary_language"].value if hasattr(data["primary_language"], "value") else data["primary_language"]
        )
    for k, v in data.items():
        setattr(p, k, v)
    await write_audit(
        session,
        action="update",
        object_type="project",
        object_id=str(p.id),
        project_id=p.id,
        user_id=user.id,
        metadata={"fields": sorted(data)},
    )
    await session.commit()
    await session.refresh(p)
    return _out(p)


@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    p = await _get_active(session, project_id)
    p.deleted_at = datetime.now(UTC)
    p.status = "deleted"
    await write_audit(
        session, action="soft_delete", object_type="project", object_id=str(p.id), project_id=p.id, user_id=user.id
    )
    await session.commit()
    return {"deleted": True}


@router.post("/{project_id}/restore", response_model=ProjectOut)
async def restore_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectOut:
    p = await session.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    p.deleted_at = None
    p.status = "active"
    await write_audit(
        session, action="restore", object_type="project", object_id=str(p.id), project_id=p.id, user_id=user.id
    )
    await session.commit()
    await session.refresh(p)
    return _out(p)


@router.get("/{project_id}/summary")
async def project_summary(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    p = await _get_active(session, project_id)
    entity_count = (
        await session.execute(select(func.count()).select_from(Entity).where(Entity.project_id == project_id))
    ).scalar_one()
    ctx_count = (
        await session.execute(
            select(func.count())
            .select_from(DiagnosticContextVersion)
            .where(DiagnosticContextVersion.project_id == project_id)
        )
    ).scalar_one()
    latest_ctx = (
        await session.execute(
            select(DiagnosticContextVersion)
            .where(DiagnosticContextVersion.project_id == project_id)
            .order_by(DiagnosticContextVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "project": _out(p).model_dump(mode="json"),
        "entity_count": entity_count,
        "context_version_count": ctx_count,
        "latest_context_status": latest_ctx.status if latest_ctx else None,
    }
