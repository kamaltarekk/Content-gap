# Operations Runbook — Cost, Metrics, Alerts, Security (spec §24, §26, §31)

## Cost & budget caps (§31.4)
- Every paid provider call is written to `cost_ledger` (tokens + USD cost; cache hits at $0). Read
  `GET /api/v1/projects/{id}/cost` for the total, cache-hit count, and per-call breakdown.
- Set a per-project cap with `PUT /api/v1/projects/{id}/budget-cap`. Once spend reaches the cap,
  `POST …/classification/run` returns **402** and no paid work is enqueued.
- Estimates are shown before execution (`…/classification/estimate`); tests run fully offline with
  the deterministic fake provider, so CI never makes a paid call.

## PII & data governance (§25.4, §31.5)
- Warn before upload: `GET /api/v1/pii/warning`.
- Redaction preview for CSV/manual text: `POST /api/v1/pii/redaction-preview` (masks emails +
  phone numbers, including Arabic-Indic digits).
- Logs and error reports are scrubbed by `app/core/log_scrub.py`: authorization headers, provider
  keys, session secrets, and all evidence/verbatim text are `[REDACTED]`, and stray PII in
  free-text fields is masked. Wire the `ErrorReporter` shim to Sentry in production — it receives
  the already-scrubbed payload.

## Project deletion & purge (§25.6)
- `DELETE /api/v1/projects/{id}` soft-deletes (7-day recovery window); `POST …/restore` reverses it.
- `POST /api/v1/projects/{id}/purge` hard-deletes the project and **all** raw + derived data via
  `ON DELETE CASCADE` (sources, snapshots, pieces, spans, classifications, VoC, claims,
  performance, diagnoses, gaps, reports, cost ledger).

## Metrics & alerts (§26)
Export these signals to the platform monitor and alert on them:
- **Job health** — queued/running/failed counts, retry rate, oldest running job age.
- **Cost** — per-project spend vs cap; alert at 80% of cap.
- **Dependencies** — Postgres reachable, Redis reachable, object storage reachable (health check).
- **Errors** — error-reporter event rate by code.

## Dependency & secret scanning (§25.5, §29)
- `.env` is gitignored; `.env.example` ships empty values; CI runs secret scanning.
- `backend/tests/test_repo_hygiene.py` asserts no real provider key and a blank example secret.
- Run dependency audits in CI (`uv pip check` / `pnpm audit`) and patch on a regular cadence.

## Load / capacity
Target: a 200-piece brand sample plus three 100-piece competitor samples complete within the
configured worker concurrency without blocking the API (all heavy work runs in jobs, §6.5). Drive
load with the offline fixtures so the check costs nothing.
