from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.enums import BuyingGroupRole as BuyingGroupRoleEnum
from app.db.models.buying_group import BuyingGroupRole
from app.db.models.project import Project
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(tags=["buying-group"])


class RoleCreate(BaseModel):
    canonical_role: BuyingGroupRoleEnum
    display_label: str = Field(min_length=1, max_length=300)
    description: str | None = None
    influence_level: int | None = Field(default=None, ge=0, le=10)
    success_definition: str | None = None
    concerns: str | None = None


class RoleUpdate(BaseModel):
    display_label: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    influence_level: int | None = Field(default=None, ge=0, le=10)
    success_definition: str | None = None
    concerns: str | None = None


class RoleOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    canonical_role: str
    display_label: str
    description: str | None
    influence_level: int | None


def _out(r: BuyingGroupRole) -> RoleOut:
    return RoleOut(
        id=r.id,
        project_id=r.project_id,
        canonical_role=r.canonical_role,
        display_label=r.display_label,
        description=r.description,
        influence_level=r.influence_level,
    )


@router.post("/api/v1/projects/{project_id}/buying-group", response_model=RoleOut, status_code=201)
async def create_role(
    project_id: uuid.UUID,
    body: RoleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RoleOut:
    if await session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    r = BuyingGroupRole(
        project_id=project_id,
        canonical_role=body.canonical_role.value,
        display_label=body.display_label,
        description=body.description,
        influence_level=body.influence_level,
        success_definition=body.success_definition,
        concerns=body.concerns,
    )
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return _out(r)


@router.get("/api/v1/projects/{project_id}/buying-group", response_model=list[RoleOut])
async def list_roles(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[RoleOut]:
    rows = (
        (
            await session.execute(
                select(BuyingGroupRole)
                .where(BuyingGroupRole.project_id == project_id)
                .order_by(BuyingGroupRole.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [_out(r) for r in rows]


@router.patch("/api/v1/buying-group/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RoleOut:
    r = await session.get(BuyingGroupRole, role_id)
    if r is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    await session.commit()
    await session.refresh(r)
    return _out(r)


@router.delete("/api/v1/buying-group/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    r = await session.get(BuyingGroupRole, role_id)
    if r is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    await session.delete(r)
    await session.commit()
    return {"deleted": True}
