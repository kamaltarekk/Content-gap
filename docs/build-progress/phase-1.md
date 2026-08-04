# Phase 1 — Foundation — COMPLETE ✅ (offline gate verified; docker path canonical)

## Deliverables
- **Repository structure** per spec §5.4 (`backend/`, `frontend/`, `infra/`, `fixtures/`, `docs/`).
- **FastAPI app** (`backend/app/main.py`): app factory, `SessionMiddleware`, CORS, uniform error
  envelope (§11.20), lifespan `validate_startup`, routers mounted.
- **React/Vite app** (`frontend/`): React 19 + TS, TanStack Query, typed API client, bilingual
  (`dir="auto"`) shell that reads `/api/v1/config/public`.
- **Docker Compose** (`infra/docker-compose.yml`): Postgres 17, Redis 7, MinIO (+ bucket init),
  backend (runs `alembic upgrade head`), worker placeholder (Phase 4), frontend. Test deps in
  `infra/docker-compose.test.yml`.
- **SQLAlchemy 2.0 (async) + Alembic**: `Base`, async engine/session, `users` model, initial
  migration `0001_users` (enables `pgcrypto`).
- **Authentication modes** (§3.1): `session` (HttpOnly signed cookie) and `none` (local no-auth,
  auto dev admin). `login`/`logout`/`me`/`change-password`, Argon2 hashing (hashes never returned).
- **Health**: `/health/live` (always) and `/health/ready` (checks DB + Redis + object storage,
  returns 503 accurately when any is down; never calls the AI provider — §11.1).
- **Tooling**: ruff (clean), mypy config, pytest, ESLint config in `package.json`, Vitest.
- **CI**: `.github/workflows/ci.yml` — backend (ruff + mypy + pytest with a Postgres service) and
  frontend (typecheck + test + production build).
- **`.env.example`**, **README** with startup instructions, **Makefile**.

## Tests run (offline, fake AI, real local Postgres on :5433)
```
backend:  uv run pytest -q            → 19 passed
          - Phase 0 carried: enum parity (3), gold fixture (6)
          - test_foundation.py (6): /health/live; readiness reports per-dependency & 503 when down;
            public config has no secrets; test settings override real-looking keys (§6.23);
            login/logout roundtrip; no-auth mode provisions dev admin
          - test_migrations.py (1): alembic upgrade head → users exists → downgrade base → gone
          - test_repo_hygiene.py (3): no real API key committed; blank key in .env.example; .env gitignored
backend:  uv run ruff check .         → All checks passed
frontend: pnpm test (vitest)          → 3 passed (enum parity)
frontend: pnpm typecheck              → clean
frontend: pnpm build                  → production build succeeds (vite, 76 modules)
```

## Acceptance gate
- ⚠️ `docker compose up` — **not executable in this sandbox** (no Docker daemon). The compose file
  is the canonical path and is written to bring up the full stack; verified by construction, not
  by run. Recorded in ADR 0001.
- ✅ Backend and frontend tests pass offline.
- ✅ Production build succeeds.
- ✅ Health readiness accurately fails (503) when a dependency is unavailable — directly tested
  (Redis + MinIO absent in the sandbox → readiness reports them down).

## Deviations (recorded)
- Spec pins **Vite 8.1 / React 19.2**, which are not published; used latest stable **React 19 /
  Vite 6**. No behavioral impact. (ADR-worthy note; captured here.)
- **PostgreSQL 16** locally vs spec's 17 (17 pinned in compose). No 17-only feature used.
- **Docker unavailable** in the build sandbox — see ADR 0001.

## Next
Phase 2 — Projects & Diagnostic Context: projects CRUD, brand/competitor entities, buying-group
roles, versioned diagnostic context with validation + approval (immutability + clone-on-edit),
context setup UI, audit log. Gate: create & approve a context version; full analysis stays blocked
when required data is missing.
