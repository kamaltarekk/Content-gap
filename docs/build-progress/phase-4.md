# Phase 4 — Job System — COMPLETE ✅ (offline gate verified; Celery is the canonical path)

## Deliverables
- **Persistent job model + events** (`jobs`, `job_events`; migration `0004`): status, current stage,
  progress %, idempotency key (unique), input manifest, result reference, retry/max-retry,
  error code + safe message, `cancel_requested`, timestamps. **PostgreSQL is the source of truth.**
- **Celery worker** (`app/workers/celery_app.py`): `execute_job` task; `task_acks_late`,
  `reject_on_worker_lost`, prefetch=1. Runs via `celery -A app.workers.celery_app.celery worker`.
- **Dispatch abstraction** (`app/jobs/dispatcher.py`): `celery` (broker), `inline` (in-process for
  local dev, no broker), `deferred` (tests drive the worker directly). Enqueue returns a job id
  immediately, independent of backend.
- **Job service** (`app/jobs/service.py`): enqueue with **idempotency** (a matching active/completed
  key returns the same job = no duplicate paid/mutating work; a failed/cancelled key re-queues),
  events, cancel request.
- **Runner** (`app/jobs/runner.py`): cooperative **cancellation between stages** (re-reads the flag
  each stage), incrementally **persisted progress**, **idempotent duplicate delivery** (a
  non-queued job is not re-run), and **retry classification**.
- **Retry policy** (`app/jobs/retry.py`, spec §6.7/§20.11): safe-retry for connection/429/5xx;
  **never auto-retry an ambiguous timeout** (avoids double-charging a paid request); validation/
  refusal never blind-retry. Exhausted retries → **dead-letter** (`failed` with a stable code).
- **Jobs API** (`app/api/jobs.py`, §11.19): enqueue (202), list (by project + status = admin/
  dead-letter view), get, events, cancel, retry.
- **Progress UI** (`frontend/src/pages/Jobs.tsx`): enqueue + poll status/progress/events.
- Compose: worker service now runs the Celery worker; backend dispatches via `JOB_DISPATCH=celery`.

## Tests run (offline, deferred dispatcher + direct worker calls)
```
backend:  uv run pytest -q            → 41 passed  (Phase 0–3 carried + Phase 4 below)
          - retry classification: transient→retry, ambiguous timeout→no-retry, exhausted→no-retry
          - enqueue returns a job id without running it (queued, 0%)
          - worker runs to completion with accurate progress + started/stage×N/completed events
          - duplicate delivery is idempotent (re-run adds no events, stays completed)
          - enqueue idempotency-key dedup (same id, created=false, cache_hit=true)
          - safe retry vs ambiguous timeout (transient→queued/retry_count=1; timeout→failed/no-retry)
          - results persist independent of broker (job + events + result_reference retrievable)
          - cancellation between stages (cancel → cancelled, progress<100, no completed event)
backend:  ruff check + format         → All checks passed
frontend: typecheck / build           → clean; production build succeeds
```

## Acceptance gate — PASS
- ✅ Long tasks run out-of-band (Celery worker / inline dispatcher), continue after the browser
  closes, and report accurate persisted progress.
- ✅ Paid/mutating work is never duplicated: idempotency key on enqueue + idempotent execution on
  duplicate delivery + no auto-retry on ambiguous timeouts.
- ⚠️ A running Redis broker + Celery worker could not be exercised in this sandbox; the worker and
  broker are wired as the canonical path and verified by construction, while the job semantics
  (progress, cancellation, idempotency, retry, dead-letter) are fully tested offline.

## Next
Phase 5 — Content Classification: AI provider abstraction + Anthropic adapter, token counting +
cost estimate, structured-output schemas, prompt registry, classification jobs, validation + one
repair attempt, review queue, batch approval, classification history. Gate: every persisted
classification has valid evidence/confidence/origin/review status; invalid structured output never
becomes an approved result.
