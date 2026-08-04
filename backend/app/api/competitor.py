from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.clients.storage import Storage, get_storage
from app.core.config import Settings, get_settings
from app.core.enums import CollectionItemStatus, ContentFormat
from app.db.models.competitor import CompetitorCollection, CompetitorDiagnosis
from app.db.models.user import User
from app.db.session import get_session
from app.services import competitor

router = APIRouter(tags=["competitor-diagnosis"])


def storage_dep(settings: Settings = Depends(get_settings)) -> Storage:
    return get_storage(settings)


class CollectItemIn(BaseModel):
    content_format: ContentFormat = ContentFormat.social_post
    text: str | None = Field(default=None, max_length=100_000)
    url: str | None = Field(default=None, max_length=2000)
    status: CollectionItemStatus | None = None


class CollectIn(BaseModel):
    items: list[CollectItemIn] = Field(min_length=1, max_length=500)
    channels: list[str] = Field(default_factory=list)
    period_start: date | None = None
    period_end: date | None = None


@router.post("/api/v1/projects/{project_id}/competitors/{entity_id}/collect", status_code=201)
async def collect(
    project_id: uuid.UUID,
    entity_id: uuid.UUID,
    body: CollectIn,
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(storage_dep),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        collection = await competitor.collect_competitor(
            session,
            storage,
            project_id=project_id,
            entity_id=entity_id,
            items=[
                competitor.CollectionItemInput(
                    content_format=i.content_format.value,
                    text=i.text,
                    url=i.url,
                    status=i.status.value if i.status else None,
                )
                for i in body.items
            ],
            channels=body.channels,
            period_start=body.period_start,
            period_end=body.period_end,
        )
    except competitor.CompetitorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = await competitor.get_collection_payload(collection, session)
    await session.commit()
    return payload


@router.get("/api/v1/projects/{project_id}/competitors/{entity_id}/collections")
async def list_collections(
    project_id: uuid.UUID, entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(CompetitorCollection)
                .where(CompetitorCollection.entity_id == entity_id)
                .order_by(CompetitorCollection.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [await competitor.get_collection_payload(c, session) for c in rows]


@router.post("/api/v1/projects/{project_id}/competitors/{entity_id}/diagnosis", status_code=201)
async def run(
    project_id: uuid.UUID,
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        diagnosis = await competitor.run_competitor_diagnosis(session, project_id, entity_id)
    except competitor.CompetitorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = await competitor.get_diagnosis_payload(session, diagnosis.id)
    await session.commit()
    return payload


@router.get("/api/v1/projects/{project_id}/competitors/{entity_id}/diagnosis")
async def list_diagnoses(
    project_id: uuid.UUID, entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(CompetitorDiagnosis)
                .where(CompetitorDiagnosis.entity_id == entity_id)
                .order_by(CompetitorDiagnosis.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {"id": str(d.id), "sample_sufficiency": d.sample_sufficiency, "sample_piece_count": d.sample_piece_count}
        for d in rows
    ]


@router.get("/api/v1/competitor-diagnosis/{diagnosis_id}")
async def get_diagnosis(diagnosis_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await competitor.get_diagnosis_payload(session, diagnosis_id)
    except competitor.CompetitorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
