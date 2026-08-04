"""Celery app + task. Canonical worker path. PostgreSQL remains the source of truth; Celery only
delivers the trigger. Run: `celery -A app.workers.celery_app.celery worker -l info`."""

from __future__ import annotations

import asyncio
import uuid

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()
celery = Celery("cdga", broker=_settings.redis_url, backend=_settings.redis_url)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)


@celery.task(name="execute_job", bind=True, max_retries=0)
def execute_job_task(self: object, job_id: str) -> None:
    from app.db.session import get_sessionmaker
    from app.jobs import handlers  # noqa: F401 - registers handlers
    from app.jobs.runner import execute_job

    async def _run() -> None:
        async with get_sessionmaker()() as session:
            await execute_job(session, uuid.UUID(job_id))

    asyncio.run(_run())
