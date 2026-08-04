from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.audit import write_audit
from app.core.enums import CompetitorType, EntityType
from app.db.models.entity import Entity
from app.db.models.project import Project
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(tags=["entities"])


class EntityCreate(BaseModel):
    entity_type: EntityType
    name: str = Field(min_length=1, max_length=300)
    competitor_type: CompetitorType | None = None
    website_url: str | None = None
    comparison_rationale: str | None = None
    notes: str | None = None
    is_primary_brand: bool = False

    @model_validator(mode="after")
    def _rules(self) -> EntityCreate:
        if self.entity_type == EntityType.brand:
            self.is_primary_brand = True
        if self.entity_type == EntityType.competitor and not (
            self.comparison_rationale and self.comparison_rationale.strip()
        ):
            raise ValueError("comparison_rationale is required for a competitor")
        return self


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    competitor_type: CompetitorType | None = None
    website_url: str | None = None
    comparison_rationale: str | None = None
    notes: str | None = None


class EntityOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    entity_type: str
    competitor_type: str | None
    name: str
    website_url: str | None
    comparison_rationale: str | None
    is_primary_brand: bool


def _out(e: Entity) -> EntityOut:
    return EntityOut(
        id=e.id,
        project_id=e.project_id,
        entity_type=e.entity_type,
        competitor_type=e.competitor_type,
        name=e.name,
        website_url=e.website_url,
        comparison_rationale=e.comparison_rationale,
        is_primary_brand=e.is_primary_brand,
    )


@router.post("/api/v1/projects/{project_id}/entities", response_model=EntityOut, status_code=201)
async def create_entity(
    project_id: uuid.UUID,
    body: EntityCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> EntityOut:
    if await session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    e = Entity(
        project_id=project_id,
        entity_type=body.entity_type.value,
        competitor_type=body.competitor_type.value if body.competitor_type else None,
        name=body.name,
        website_url=body.website_url,
        comparison_rationale=body.comparison_rationale,
        notes=body.notes,
        is_primary_brand=body.is_primary_brand,
    )
    session.add(e)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        # Either duplicate name or the one-primary-brand partial unique index.
        detail = "one_primary_brand_per_project" if body.is_primary_brand else "entity_name_conflict"
        raise HTTPException(status_code=409, detail=detail) from exc
    await write_audit(
        session, action="create", object_type="entity", object_id=str(e.id), project_id=project_id, user_id=user.id
    )
    await session.commit()
    await session.refresh(e)
    return _out(e)


@router.get("/api/v1/projects/{project_id}/entities", response_model=list[EntityOut])
async def list_entities(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[EntityOut]:
    rows = (
        (await session.execute(select(Entity).where(Entity.project_id == project_id).order_by(Entity.created_at)))
        .scalars()
        .all()
    )
    return [_out(e) for e in rows]


@router.get("/api/v1/entities/{entity_id}", response_model=EntityOut)
async def get_entity(entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> EntityOut:
    e = await session.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="entity_not_found")
    return _out(e)


@router.patch("/api/v1/entities/{entity_id}", response_model=EntityOut)
async def update_entity(
    entity_id: uuid.UUID,
    body: EntityUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> EntityOut:
    e = await session.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="entity_not_found")
    data = body.model_dump(exclude_unset=True)
    if "competitor_type" in data and data["competitor_type"] is not None:
        data["competitor_type"] = (
            data["competitor_type"].value if hasattr(data["competitor_type"], "value") else data["competitor_type"]
        )
    for k, v in data.items():
        setattr(e, k, v)
    await write_audit(
        session,
        action="update",
        object_type="entity",
        object_id=str(e.id),
        project_id=e.project_id,
        user_id=user.id,
        metadata={"fields": sorted(data)},
    )
    await session.commit()
    await session.refresh(e)
    return _out(e)


@router.delete("/api/v1/entities/{entity_id}")
async def delete_entity(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    e = await session.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="entity_not_found")
    await write_audit(
        session, action="delete", object_type="entity", object_id=str(e.id), project_id=e.project_id, user_id=user.id
    )
    await session.delete(e)
    await session.commit()
    return {"deleted": True}
