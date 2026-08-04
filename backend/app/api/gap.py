from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models.gap import Gap, GapAnalysisRun
from app.db.models.user import User
from app.db.session import get_session
from app.services import gap_engine

router = APIRouter(tags=["gap-engine"])


@router.post("/api/v1/projects/{project_id}/gap-analysis", status_code=201)
async def run(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        run = await gap_engine.run_gap_analysis(session, project_id)
    except gap_engine.GapEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = await gap_engine.get_run_payload(session, run.id)
    await session.commit()
    return payload


@router.get("/api/v1/projects/{project_id}/gap-analysis")
async def list_runs(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(GapAnalysisRun)
                .where(GapAnalysisRun.project_id == project_id)
                .order_by(GapAnalysisRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [{"id": str(r.id), "rule_version": r.rule_version, "primary_bottleneck": r.primary_bottleneck} for r in rows]


@router.get("/api/v1/gap-analysis/{run_id}")
async def get_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await gap_engine.get_run_payload(session, run_id)
    except gap_engine.GapEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/v1/gaps/{gap_id}/approve")
async def approve(
    gap_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    gap = await session.get(Gap, gap_id)
    if gap is None:
        raise HTTPException(status_code=404, detail="gap_not_found")
    await gap_engine.approve_gap(session, gap, user.id)
    await session.commit()
    return gap_engine._gap_out(gap)
