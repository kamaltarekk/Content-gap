# Migration Runbook (spec §31.6)

Schema changes are Alembic migrations under `backend/alembic/versions/`. Every migration is
tested by `backend/tests/test_migrations.py` (full `downgrade base → upgrade head → downgrade base
→ upgrade head` against a scratch database), and the migration head must stay in lock-step with the
ORM models.

## Current migration chain
`0001_initial` → `0002…` → … → `0011_cost_ledger_budget` (head).

## Applying migrations
```bash
cd backend
DATABASE_URL=postgresql+asyncpg://cgi:cgi@$DB_HOST:5432/cdga \
  uv run --python 3.12 alembic upgrade head
```
The app derives a sync (`+psycopg`) URL from `DATABASE_URL` for Alembic automatically.

## Authoring a new migration
1. Change the SQLAlchemy models under `app/db/models/` and register them in `models/__init__.py`.
2. Write a hand-authored migration (revision + `down_revision` pointing at the prior head). Prefer
   explicit `op.*` calls over autogenerate so the migration reads clearly and reverses cleanly.
3. Provide a real `downgrade()` — the migration test exercises it.
4. Run `uv run --python 3.12 pytest tests/test_migrations.py`.

## Rollback procedure
- Roll back one revision:
  ```bash
  uv run --python 3.12 alembic downgrade -1
  ```
- If a deploy must be reverted, downgrade to the previous release's head **before** rolling back
  application code, so the running code never sees a newer schema it cannot read.
- Data-destructive downgrades (dropping a populated column/table) require a fresh backup first
  (see `backup-and-restore.md`) and an explicit go/no-go.

## Migration-from-previous-version test
`test_migration_upgrade_and_downgrade` runs the full chain on a scratch `cdga_migrate` database and
asserts the schema is created and torn down cleanly. Keep it green before every release.
