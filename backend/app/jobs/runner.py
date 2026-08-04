"""Job execution runner: cooperative cancellation between stages, accurate persisted progress,
idempotent duplicate-delivery handling, and deterministic retry classification."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import Job
from app.jobs import service
from app.jobs.retry import classify

_TERMINAL = {"completed", "completed_with_warnings", "cancelled", "failed"}


class JobCancelled(Exception):
    pass


class StageRunner:
    def __init__(self, session: AsyncSession, job: Job) -> None:
        self.session = session
        self.job = job

    async def stage(self, name: str, progress: int) -> None:
        # Cooperative cancellation: re-read the flag (it may be set by another request/session).
        cancel = (await self.session.execute(select(Job.cancel_requested).where(Job.id == self.job.id))).scalar_one()
        if cancel:
            raise JobCancelled(name)
        self.job.current_stage = name
        self.job.progress_percent = max(0, min(100, progress))
        await service.add_event(self.session, self.job, "stage", stage=name, progress=self.job.progress_percent)
        await self.session.commit()  # persist progress incrementally (survives broker loss)


JobHandler = Callable[[StageRunner, Job], Awaitable[list[str]]]
HANDLERS: dict[str, JobHandler] = {}


def register(job_type: str) -> Callable[[JobHandler], JobHandler]:
    def deco(fn: JobHandler) -> JobHandler:
        HANDLERS[job_type] = fn
        return fn

    return deco


async def execute_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    job = await session.get(Job, job_id)
    if job is None:
        return None
    # Idempotent duplicate delivery (spec §6.6): a job not freshly queued is not re-run.
    if job.status != "queued":
        return job

    handler = HANDLERS.get(job.job_type)
    job.status = "running"
    job.started_at = service.now()
    await service.add_event(session, job, "started")
    await session.commit()

    if handler is None:
        job.status = "failed"
        job.error_code = "unknown_job_type"
        job.completed_at = service.now()
        await service.add_event(session, job, "failed", message=job.error_code)
        await session.commit()
        return job

    try:
        warnings = await handler(StageRunner(session, job), job)
    except JobCancelled as exc:
        job.status = "cancelled"
        job.completed_at = service.now()
        await service.add_event(session, job, "cancelled", stage=str(exc))
        await session.commit()
        return job
    except Exception as exc:  # noqa: BLE001 - classified below
        decision = classify(exc, retry_count=job.retry_count, max_retries=job.max_retries)
        if decision.should_retry:
            job.retry_count += 1
            job.status = "queued"  # re-queued; a worker/dispatcher picks it up again
            await service.add_event(
                session, job, "retry_scheduled", message=decision.error_code, metadata={"attempt": job.retry_count}
            )
        else:
            job.status = "failed"  # dead-letter: stays failed with a stable error code (§22.5)
            job.error_code = decision.error_code
            job.error_message_safe = decision.reason
            job.completed_at = service.now()
            await service.add_event(session, job, "failed", message=decision.error_code)
        await session.commit()
        return job

    job.status = "completed_with_warnings" if warnings else "completed"
    job.progress_percent = 100
    job.completed_at = service.now()
    if warnings:
        job.result_reference = {"warnings": warnings}
    await service.add_event(session, job, job.status, progress=100, metadata={"warnings": warnings})
    await session.commit()
    return job
