from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models.brand_diagnosis import BrandDiagnosis
from app.db.models.user import User
from app.db.session import get_session
from app.services import brand_diagnosis

router = APIRouter(tags=["brand-diagnosis"])


@router.post("/api/v1/projects/{project_id}/brand-diagnosis", status_code=201)
async def run(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        diagnosis = await brand_diagnosis.run_brand_diagnosis(session, project_id)
    except brand_diagnosis.BrandDiagnosisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = await brand_diagnosis.get_diagnosis_payload(session, diagnosis.id)
    await session.commit()
    return payload


@router.get("/api/v1/projects/{project_id}/brand-diagnosis")
async def list_diagnoses(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(BrandDiagnosis)
                .where(BrandDiagnosis.project_id == project_id)
                .order_by(BrandDiagnosis.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {"id": str(d.id), "readiness_grade": d.readiness_grade, "primary_bottleneck": d.primary_bottleneck}
        for d in rows
    ]


@router.get("/api/v1/brand-diagnosis/{diagnosis_id}")
async def get_diagnosis(diagnosis_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await brand_diagnosis.get_diagnosis_payload(session, diagnosis_id)
    except brand_diagnosis.BrandDiagnosisError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
