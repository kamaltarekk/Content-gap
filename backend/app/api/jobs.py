from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.models.job import Job, JobEvent
from app.db.models.user import User
from app.db.session import get_session
from app.jobs import service
from app.jobs.dispatcher import Dispatcher, get_dispatcher

router = APIRouter(tags=["jobs"])


def dispatcher_dep(settings: Settings = Depends(get_settings)) -> Dispatcher:
    return get_dispatcher(settings)


def _job_out(j: Job) -> dict:
    return {
        "id": str(j.id),
        "project_id": str(j.project_id) if j.project_id else None,
        "job_type": j.job_type,
        "status": j.status,
        "current_stage": j.current_stage,
        "progress_percent": j.progress_percent,
        "retry_count": j.retry_count,
        "error_code": j.error_code,
        "result_reference": j.result_reference,
        "cancel_requested": j.cancel_requested,
    }


class EnqueueJobIn(BaseModel):
    job_type: str = Field(min_length=1, max_length=50)
    input_manifest: dict = Field(default_factory=dict)
    max_retries: int = Field(default=0, ge=0, le=5)
    project_id: uuid.UUID | None = None


@router.post("/api/v1/jobs", status_code=202)
async def enqueue(
    body: EnqueueJobIn,
    session: AsyncSession = Depends(get_session),
    dispatcher: Dispatcher = Depends(dispatcher_dep),
    user: User = Depends(get_current_user),
) -> dict:
    """Enqueue a job and return its id immediately (worker executes out-of-band)."""
    job, created = await service.enqueue_job(
        session,
        project_id=body.project_id,
        job_type=body.job_type,
        input_manifest=body.input_manifest,
        max_retries=body.max_retries,
    )
    await session.commit()
    if created:
        dispatcher.dispatch(job.id)
    return {"job_id": str(job.id), "status": job.status, "created": created, "cache_hit": not created}


@router.get("/api/v1/projects/{project_id}/jobs")
async def list_jobs(
    project_id: uuid.UUID,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(Job).where(Job.project_id == project_id).order_by(Job.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    if status:
        rows = [r for r in rows if r.status == status]
    return [_job_out(j) for j in rows]


@router.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    j = await session.get(Job, job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return _job_out(j)


@router.get("/api/v1/jobs/{job_id}/events")
async def get_job_events(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (await session.execute(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id))).scalars().all()
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "stage": e.stage,
            "progress_percent": e.progress_percent,
            "message": e.message_safe,
            "metadata": e.event_metadata,
        }
        for e in rows
    ]


@router.post("/api/v1/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    j = await session.get(Job, job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    await service.request_cancel(session, j)
    await session.commit()
    return {"cancel_requested": True, "status": j.status}


@router.post("/api/v1/jobs/{job_id}/retry", status_code=202)
async def retry_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    dispatcher: Dispatcher = Depends(dispatcher_dep),
    user: User = Depends(get_current_user),
) -> dict:
    j = await session.get(Job, job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    if j.status not in {"failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="job_not_retryable")
    j.status = "queued"
    j.error_code = None
    j.error_message_safe = None
    j.cancel_requested = False
    await service.add_event(session, j, "retry_requested")
    await session.commit()
    dispatcher.dispatch(j.id)
    return {"job_id": str(j.id), "status": j.status}
