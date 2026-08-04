from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from app.db.models.job import Job, JobEvent
from app.db.session import get_sessionmaker
from app.jobs import handlers  # noqa: F401 - registers the demo handler
from app.jobs.retry import (
    AmbiguousTimeoutError,
    TransientConnectionError,
    classify,
)
from app.jobs.runner import execute_job
from tests.conftest import requires_db

# asyncio_mode=auto marks async tests automatically; requires_db skips when no DB.
pytestmark = [requires_db]


async def _run_worker(job_id: uuid.UUID) -> Job | None:
    async with get_sessionmaker()() as session:
        return await execute_job(session, job_id)


async def _enqueue(client: AsyncClient, manifest: dict, max_retries: int = 0) -> str:
    r = await client.post(
        "/api/v1/jobs",
        json={"job_type": "demo", "input_manifest": manifest, "max_retries": max_retries},
    )
    assert r.status_code == 202, r.text
    return r.json()["job_id"]


def test_retry_policy_classification() -> None:
    # Safe to retry when attempts remain; not safe on an ambiguous timeout.
    d = classify(TransientConnectionError(), retry_count=0, max_retries=2)
    assert d.should_retry and d.error_code == "connection_failed"
    d2 = classify(AmbiguousTimeoutError(), retry_count=0, max_retries=2)
    assert d2.should_retry is False and d2.error_code == "timeout_unknown_completion"
    d3 = classify(TransientConnectionError(), retry_count=2, max_retries=2)
    assert d3.should_retry is False  # exhausted


async def test_enqueue_returns_job_id_without_running(noauth_client: AsyncClient) -> None:
    job_id = await _enqueue(noauth_client, {"stages": ["a", "b"]})
    # Deferred dispatcher: the job is queued, not executed by the request.
    got = (await noauth_client.get(f"/api/v1/jobs/{job_id}")).json()
    assert got["status"] == "queued"
    assert got["progress_percent"] == 0


async def test_worker_runs_to_completion_with_progress(noauth_client: AsyncClient) -> None:
    job_id = await _enqueue(noauth_client, {"stages": ["load", "process", "persist"]})
    job = await _run_worker(uuid.UUID(job_id))
    assert job is not None and job.status == "completed"
    assert job.progress_percent == 100
    events = (await noauth_client.get(f"/api/v1/jobs/{job_id}/events")).json()
    types = [e["event_type"] for e in events]
    assert "started" in types and types.count("stage") == 3 and "completed" in types


async def test_duplicate_delivery_is_idempotent(noauth_client: AsyncClient) -> None:
    job_id = await _enqueue(noauth_client, {"stages": ["a", "b"]})
    await _run_worker(uuid.UUID(job_id))
    async with get_sessionmaker()() as session:
        before = (
            await session.execute(
                select(func.count()).select_from(JobEvent).where(JobEvent.job_id == uuid.UUID(job_id))
            )
        ).scalar_one()
    # Deliver the same task again — must be a no-op (spec §6.6).
    await _run_worker(uuid.UUID(job_id))
    async with get_sessionmaker()() as session:
        after = (
            await session.execute(
                select(func.count()).select_from(JobEvent).where(JobEvent.job_id == uuid.UUID(job_id))
            )
        ).scalar_one()
        job = await session.get(Job, uuid.UUID(job_id))
    assert before == after  # no new events
    assert job is not None and job.status == "completed"


async def test_enqueue_idempotency_key_dedup(noauth_client: AsyncClient) -> None:
    manifest = {"stages": ["a"], "tag": "same"}
    first = await noauth_client.post("/api/v1/jobs", json={"job_type": "demo", "input_manifest": manifest})
    second = await noauth_client.post("/api/v1/jobs", json={"job_type": "demo", "input_manifest": manifest})
    assert first.json()["job_id"] == second.json()["job_id"]
    assert second.json()["created"] is False and second.json()["cache_hit"] is True


async def test_safe_retry_vs_ambiguous_timeout(noauth_client: AsyncClient) -> None:
    # Transient fault with a retry budget → re-queued, retry_count incremented.
    tid = await _enqueue(
        noauth_client, {"stages": ["a", "b"], "raise_at": {"stage": "b", "kind": "transient"}}, max_retries=1
    )
    tjob = await _run_worker(uuid.UUID(tid))
    assert tjob is not None and tjob.status == "queued" and tjob.retry_count == 1

    # Ambiguous timeout → failed, NO auto-retry (never double-charge a paid request).
    toid = await _enqueue(
        noauth_client, {"stages": ["a"], "raise_at": {"stage": "a", "kind": "timeout"}}, max_retries=3
    )
    tojob = await _run_worker(uuid.UUID(toid))
    assert tojob is not None and tojob.status == "failed"
    assert tojob.error_code == "timeout_unknown_completion" and tojob.retry_count == 0


async def test_results_persist_independent_of_broker(noauth_client: AsyncClient) -> None:
    # PostgreSQL is the source of truth: after completion, job + events are retrievable without
    # any broker/cache involvement (spec §6.8).
    job_id = await _enqueue(noauth_client, {"stages": ["a", "b"], "warn": True})
    job = await _run_worker(uuid.UUID(job_id))
    assert job is not None and job.status == "completed_with_warnings"
    got = (await noauth_client.get(f"/api/v1/jobs/{job_id}")).json()
    assert got["status"] == "completed_with_warnings"
    assert got["result_reference"]["warnings"] == ["demo_warning"]
    assert len((await noauth_client.get(f"/api/v1/jobs/{job_id}/events")).json()) > 0


async def test_cancellation_between_stages(noauth_client: AsyncClient) -> None:
    job_id = await _enqueue(noauth_client, {"stages": ["a", "b", "c", "d"]})
    # Request cancellation before the worker runs.
    assert (await noauth_client.post(f"/api/v1/jobs/{job_id}/cancel")).status_code == 200
    job = await _run_worker(uuid.UUID(job_id))
    assert job is not None and job.status == "cancelled"
    assert job.progress_percent < 100  # stopped cooperatively, not all stages ran
    events = [e["event_type"] for e in (await noauth_client.get(f"/api/v1/jobs/{job_id}/events")).json()]
    assert "cancelled" in events and "completed" not in events
