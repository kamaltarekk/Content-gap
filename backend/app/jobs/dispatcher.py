"""Job dispatch. Separates "enqueue returns fast" from "worker executes" so the API can return a
job id within milliseconds (spec §6.5) regardless of backend."""

from __future__ import annotations

import asyncio
import uuid
from typing import Protocol

from app.core.config import Settings, get_settings


class Dispatcher(Protocol):
    def dispatch(self, job_id: uuid.UUID) -> None: ...


class DeferredDispatcher:
    """Records dispatches without running them. Used by tests, which call execute_job directly."""

    def __init__(self) -> None:
        self.dispatched: list[uuid.UUID] = []

    def dispatch(self, job_id: uuid.UUID) -> None:
        self.dispatched.append(job_id)


class InlineDispatcher:
    """Runs the job in-process on the event loop (local dev without a broker). Fire-and-forget so
    the request returns immediately; execution uses its own DB session."""

    def dispatch(self, job_id: uuid.UUID) -> None:
        asyncio.create_task(self._run(job_id))

    async def _run(self, job_id: uuid.UUID) -> None:
        from app.db.session import get_sessionmaker
        from app.jobs import handlers  # noqa: F401 - registers handlers
        from app.jobs.runner import execute_job

        async with get_sessionmaker()() as session:
            await execute_job(session, job_id)


class CeleryDispatcher:
    def dispatch(self, job_id: uuid.UUID) -> None:
        from app.workers.celery_app import execute_job_task

        execute_job_task.delay(str(job_id))


def get_dispatcher(settings: Settings | None = None) -> Dispatcher:
    settings = settings or get_settings()
    if settings.job_dispatch == "celery":
        return CeleryDispatcher()
    if settings.job_dispatch == "deferred":
        return DeferredDispatcher()
    return InlineDispatcher()
