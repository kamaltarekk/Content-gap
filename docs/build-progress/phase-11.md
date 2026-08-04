# Phase 11 — Security, Cost, and Operational Hardening — COMPLETE ✅

## Deliverables
- **Cost ledger** (`cost_ledger` table, migration `0011`): one row per paid provider call with
  token counts + USD cost; cache hits log at $0; no prompt/evidence text is ever stored. Wired into
  `classify_piece` so every classification call is recorded. `GET /projects/{id}/cost` shows the
  total, cache-hit count, and per-call breakdown.
- **Configurable budget caps**: `projects.budget_cap_usd`; `PUT /projects/{id}/budget-cap` sets it;
  `check_budget` blocks `POST …/classification/run` with **402** once spend reaches the cap.
- **PII warnings + redaction preview** (`app/core/pii.py`): `GET /pii/warning` and
  `POST /pii/redaction-preview` mask emails and phone numbers (including Arabic-Indic digits) so
  users can review CSV/manual text before upload.
- **No raw PII in logs** (`app/core/log_scrub.py`): `scrub` redacts authorization headers, provider
  keys, session secrets, and all evidence/verbatim text, and masks stray PII in free-text fields; a
  Sentry-compatible `ErrorReporter` shim receives only scrubbed payloads.
- **Project purge** (`app/services/purge.py`): `POST /projects/{id}/purge` hard-deletes the project
  and **all** raw + derived data via `ON DELETE CASCADE` (soft-delete + 7-day restore already ship
  on the projects DELETE endpoint).
- **Runbooks** (`docs/runbooks/`): backup-and-restore, migrations (+ rollback), and operations
  (cost, PII, purge, metrics/alerts, dependency/secret scanning, load target).
- **UI**: a Cost & Ops page (`frontend/src/pages/CostOps.tsx`) showing the cost ledger with cache
  status, a budget-cap control, a PII redaction preview, and project purge.

## Tests run (offline, no key)
```
backend:  uv run pytest -q            → 111 passed  (Phase 0–10 carried + Phase 11 below)
          - redact emails + phones (Arabic-Indic digits) [Security gate]
          - scrub removes secrets + evidence; keeps non-sensitive fields [GATE: no raw PII in logs]
          - error reporter scrubs before capture
          - no paid call on page load: read endpoints leave the ledger empty [Cost gate]
          - classification logs provider cost (call_count=1, cost>0) [Cost gate]
          - budget-cap block: run returns 402 once spend >= cap [GATE: budget caps work]
          - check_budget raises BudgetExceeded (pure)
          - PII warning + redaction preview mask email/phone [Security gate]
          - project purge removes project + all derived rows (cascade) [GATE: purge works]
backend:  ruff check + format         → All checks passed
          alembic upgrade→downgrade→upgrade (0001–0011)  → passes [Recovery gate: migration test]
          repo hygiene: no real key committed; .env.example blank [Security gate: secret scanning]
frontend: enum parity / typecheck / build → 3 parity tests pass; production build succeeds
```

## Acceptance gate — PASS (Section 31 production gates)
- ✅ **Cost gate (§31.4)** — no paid call on page load; cost estimate before execution; cache +
  fingerprints work (Phase 5); budget caps block at the cap; tests are offline; provider cost is
  logged.
- ✅ **Security gate (§31.5)** — production auth (Phase 1); secrets outside the repo (hygiene test);
  private object storage (Phase 3); **no raw PII in logs**; project isolation (Phase 2);
  **project purge works**; prompt-injection tests pass (Phase 5).
- ✅ **Recovery gate (§31.6)** — migration test passes; backup + restore and rollback procedures
  documented in the runbooks.
- ✅ Evidence / Method / Reliability gates remain green from Phases 3–10 (evidence traceability,
  severity/confidence separation, competitor limitations, non-content separation, jobs).

## Next
Phase 12 — Polish and Documentation: responsive layouts, accessibility review, empty states, error
recovery UX, demo fixture seeding, operator + methodology manuals, full README, and the
architecture-decision record.
