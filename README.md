# Evidence-Based Content Diagnosis & Competitive Gap Analysis

An Arabic-first, bilingual web application that diagnoses whether a brand's existing content can
support **one defined buying decision for one primary segment**, compares it with up to three
competitors **using only the public/uploaded evidence collected**, and identifies evidence-backed
content gaps — with every finding traceable to an exact source span.

It is **not** an SEO topic tool and **not** a content generator. AI is used only inside controlled
extraction/classification steps; **AI output is never treated as evidence**. Severity and
confidence are always separate; a competitor is never claimed to "not do X" — only "no evidence in
the analyzed sample."

> Build status: **Phase 0 (Freeze the Method)** and **Phase 1 (Foundation)** complete and green.
> See `docs/build-progress/`. The build proceeds phase-by-phase per the spec (Section 27); each
> phase ships working before the next begins.

## Architecture
Modular monolith (FastAPI) + separate Celery workers (added Phase 4). PostgreSQL, Redis (broker +
cache), MinIO/S3 object storage. React 19 + Vite frontend. See `docs/methodology/` for the frozen
method, `docs/schemas/enums.json` for the canonical enum registry, and
`docs/architecture-decisions/` for decisions.

```
backend/   FastAPI app (app/), Alembic (alembic/), tests (tests/)
frontend/  React + Vite + TypeScript
infra/     docker-compose (full stack + test deps)
fixtures/  gold-standard bilingual diagnosis fixture
docs/      methodology, schemas, build-progress, ADRs
```

## Prerequisites
- Python 3.12, `uv` · Node 22, `pnpm` · Docker (for the full stack) · PostgreSQL 17 (via Docker)

## Quick start (full stack — canonical)
```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
# API  → http://localhost:3001  (health: /health/live, /health/ready; docs: /docs)
# Web  → http://localhost:5173
```
The backend container runs `alembic upgrade head` on start. No AI or collection work runs on page
load — every provider call and collection requires an explicit user action.

## Local development without Docker
```bash
# Postgres 17 (or a local Postgres with a `cdga` + `cdga_test` database)
# Backend
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 3001
# Frontend
cd ../frontend && pnpm install && pnpm dev
```

## Tests
```bash
# Test dependencies (Postgres on :5433, Redis on :6390)
docker compose -f infra/docker-compose.test.yml up -d     # or use a local Postgres on :5433

cd backend && uv run pytest -q            # backend unit + integration (offline; fake AI)
cd ../frontend && pnpm test               # frontend (vitest) — enum parity, etc.
cd ../frontend && pnpm build              # production build gate
```
Tests force offline configuration and a test database even if real provider keys are present in
the shell.

## Environment
See `.env.example`. `AUTH_MODE=none` is local no-auth development; production requires
`AUTH_MODE=session` with a strong `SESSION_SECRET` (validated on startup). The Anthropic key lives
only in backend env and is never exposed to the client or logged.

## Known limitations (current phases)
- Docker could not be executed in the original build sandbox, so the `docker compose up` gate is
  provided as the canonical path and verified by construction; offline test halves are run
  directly (see `docs/build-progress/phase-1.md` and ADR 0001).
- Spec-pinned `Vite 8.1` / `React 19.2` are not yet published; the project uses the latest stable
  React 19 / Vite 6 (recorded in the Phase 1 report).
- Celery workers, the full data model, ingestion, classification, diagnosis, gaps, and reports
  arrive in Phases 4–10.
