# ADR 0001 — Repository placement and local environment deviations

**Status:** accepted · **Date:** 2026-08-04

## Context
This repository previously held an unrelated TypeScript product. The user directed a fresh build
of the **Evidence-Based Content Diagnosis & Competitive Gap Analysis** MVP per its build spec,
"replacing prior work" on the **same branch** (`claude/content-gap-extension-v0-eyd9i9`).

The spec's Section 5.2 assumes PostgreSQL 17+, Redis 7, MinIO, and Docker Compose for the local
stack. This sandbox has: Python 3.12, Node 22, PostgreSQL 16 (running locally, with pgvector),
`uv`/`poetry`/`pnpm`, but **no running Docker daemon**, and Redis/MinIO are not pre-installed.

## Decisions
1. **Placement.** Prior TypeScript work was moved to `legacy/` (also preserved in git history) and
   the new system is built at the clean repo root exactly per the spec's Section 5.4 layout
   (`backend/`, `frontend/`, `infra/`, `fixtures/`, `docs/`, `scripts/`).
2. **Database version.** `infra/docker-compose.yml` pins PostgreSQL 17 as the spec requires; local
   development in this sandbox may run against PostgreSQL 16 with pgvector where Docker is
   unavailable. No schema feature depends on a 17-only capability at Phase 0/1.
3. **Docker availability.** Where the sandbox cannot run `docker compose up`, phases whose
   acceptance gate is offline (Phase 0, and the offline test halves of later phases) are verified
   directly with `uv`/`pnpm`; the docker-based gate is documented per phase and remains the
   canonical path for a normal environment.

## Consequences
- These are environment/placement decisions only. They do **not** change the domain model, enums,
  scoring rules, gap taxonomy, or approval gates — those remain exactly as specified.
- Any future change that affects diagnostic meaning will get its own ADR and stop for approval.
