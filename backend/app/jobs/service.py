"""Job persistence + lifecycle. PostgreSQL is the source of truth (spec §6.8): job state,
events, and results survive broker/cache loss."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import sha256_text
from app.db.models.job import Job, JobEvent

_ACTIVE_OR_DONE = {"queued", "running", "waiting_for_review", "completed", "completed_with_warnings"}


def compute_idempotency_key(job_type: str, input_manifest: dict[str, Any]) -> str:
    return sha256_text(job_type + "|" + json.dumps(input_manifest, sort_keys=True, ensure_ascii=False))


async def enqueue_job(
    session: AsyncSession,
    *,
    project_id: uuid.UUID | None,
    job_type: str,
    input_manifest: dict[str, Any] | None = None,
    max_retries: int = 0,
    idempotency_key: str | None = None,
) -> tuple[Job, bool]:
    """Create (or reuse) a job. Returns (job, created). Idempotency prevents duplicate paid/mutating
    work: a matching key that is active or completed is returned as-is; a failed/cancelled one is
    reset to queued for a fresh attempt."""
    manifest = input_manifest or {}
    key = idempotency_key or compute_idempotency_key(job_type, manifest)
    existing = (await session.execute(select(Job).where(Job.idempotency_key == key))).scalar_one_or_none()
    if existing is not None:
        if existing.status in _ACTIVE_OR_DONE:
            return existing, False
        # failed/cancelled → re-enqueue the same job row (keeps the stable key).
        existing.status = "queued"
        existing.error_code = None
        existing.error_message_safe = None
        existing.cancel_requested = False
        existing.progress_percent = 0
        existing.current_stage = None
        existing.completed_at = None
        return existing, True

    job = Job(
        project_id=project_id,
        job_type=job_type,
        status="queued",
        idempotency_key=key,
        input_manifest=manifest,
        max_retries=max_retries,
    )
    session.add(job)
    await session.flush()
    await add_event(session, job, "queued", message="job queued")
    return job, True


async def add_event(
    session: AsyncSession,
    job: Job,
    event_type: str,
    *,
    stage: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        JobEvent(
            job_id=job.id,
            event_type=event_type,
            stage=stage,
            progress_percent=progress,
            message_safe=message,
            event_metadata=metadata or {},
        )
    )


async def request_cancel(session: AsyncSession, job: Job) -> None:
    job.cancel_requested = True
    await add_event(session, job, "cancel_requested", message="cancellation requested")


def now() -> datetime:
    return datetime.now(UTC)
