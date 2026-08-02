# Implementation Plan — Content Gap Intelligence v0

Living checklist. Updated as work proceeds. `[x]` done · `[~]` partial · `[ ]` todo.

## Hypothesis under test
> An automated system can identify content gaps that experienced marketers
> consider commercially relevant, evidence-backed, non-duplicative, and actionable.

This is a **v0 experiment**. It operates automatically but never claims autonomous
certainty or ground truth. Priority numbers are a transparent heuristic, not confidence.

## Phase 0 — Planning & scaffolding
- [x] Inspect repository (empty repo, branch `claude/content-gap-extension-v0-eyd9i9`)
- [x] Root workspace: `pnpm-workspace.yaml`, `turbo.json`, `tsconfig.base.json`, `.env.example`
- [x] `docker-compose.yml` (Postgres + pgvector, port 5433)
- [x] `IMPLEMENTATION_PLAN.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `COST_MODEL.md`, `RISK_REGISTER.md`

## Phase 1 — `@cgi/shared` (contracts)
- [x] Enums (owner_type, signal_type, journey_stage, coverage_status, gap_type, evidence_status, evidence_role, priority_label, evaluation ratings)
- [x] Zod schemas for every external + LLM-generated payload
- [x] Safety limits + config loader
- [x] Deterministic helpers: URL normalization, content hashing, date parsing

## Phase 2 — `@cgi/database`
- [x] Drizzle schema for all required entities
- [x] pgvector column for chunk embeddings
- [x] SQL migration (idempotent, creates extension)
- [x] Migrate + seed runner scripts
- [x] Connection pool + typed client

## Phase 3 — `@cgi/llm`
- [x] Provider interface (`LlmProvider`, `EmbeddingProvider`)
- [x] Deterministic **fake** LLM provider (evidence-grounded, injection-safe)
- [x] Anthropic provider (official SDK, env-driven, structured-output + Zod)
- [x] Local multilingual embedding provider (Arabic/English/mixed, no paid API)
- [x] Prompt builder with strict system/data separation + injection defenses

## Phase 4 — `@cgi/crawler`
- [x] HTTP fetch → Readability (JSDOM) → Cheerio fallback normalization
- [x] robots.txt respect, per-domain rate limiting, descriptive UA
- [x] File parsers (txt/md/csv/json), sitemap parsing
- [x] Playwright fallback (opt-in, guarded)

## Phase 5 — `@cgi/analysis-engine` (the one observable pipeline)
- [x] Stage contracts (typed in/out, versioned, logged, resumable)
- [x] Ingestion → Normalization → Chunking → Extraction → Semantic dedup
- [x] Required Decision-Support Map → Coverage Matrix
- [x] Candidate Gap Generation → Evidence Verification → Rejection/Critique
- [x] Transparent Prioritization → Report Publication (max 10)
- [x] Deterministic priority formula + evidence-status rules + shadow sample

## Phase 6 — `@cgi/test-fixtures`
- [x] Synthetic bilingual demo project (brief, offer, 2 cohorts, 10 owned, 20+ VoC,
      15 competitor assets, injection attempt, outdated asset, unsupported claim, strong proof)
- [x] Deterministic fake-LLM fixtures for the demo

## Phase 7 — `apps/api` (Fastify)
- [x] `/api/v1` versioned routes (projects, brief, cohorts, sources, runs, gaps, coverage,
      evaluations, shadow-sample, tokens, health)
- [x] Project-scoped token auth (hashed at rest)
- [x] Zod validation on every boundary; OpenAPI generation
- [x] Auto-trigger analysis on ingestion (no "Run Analysis" button)

## Phase 8 — `apps/worker` (pg-boss)
- [x] Job queues: ingest, analyze, weekly-refresh
- [x] Weekly scheduler (content-hash diff → targeted reprocessing)
- [x] Runs when extension is closed; run history + failure isolation
- [x] `demo` command: seed + full pipeline with fake providers

## Phase 9 — `apps/web` (React/Vite dashboard)
- [x] Setup wizard (project, brief, offer, cohorts, sources, VoC, competitors)
- [x] Top-10 gaps + component breakdown, coverage matrix, evidence, run history
- [x] Evaluation mode + shadow sample + outcome tracking
- [x] Continuation-criteria report

## Phase 10 — `apps/extension` (WXT / MV3 / Side Panel)
- [x] Connection view, current-page capture, gap view, source status
- [x] Minimal permissions (sidePanel, storage, activeTab, scripting), runtime host perms

## Phase 11 — Verify
- [x] Unit + integration tests (Vitest), full fake-LLM pipeline test
- [x] `tsc` typecheck, build
- [~] Playwright dashboard E2E (smoke; headless env constraints noted)

## Phase 12 — Docs & ship
- [x] README with exact commands
- [x] Commit logically grouped changes; push to designated branch

## Verified milestones (actually run)
- `pnpm install`, migrations, seed, and full fake-LLM pipeline all run green.
- Demo produces exactly 10 published gaps, STRONG_EVIDENCE on the implementation-complexity
  objection, Arabic + English gaps, exact-quote evidence, injection attempt ignored.

## Key simplifications (justified)
- **turbo** used for task running (allowed by stack). Kept minimal.
- **Embeddings**: a deterministic local multilingual embedding (char n-gram hashing into
  `EMBEDDING_DIM` buckets, L2-normalized) rather than a downloaded transformer model.
  Rationale: "no paid embedding API", works offline/deterministically for Arabic+English+mixed,
  keeps the demo + tests hermetic. The provider interface allows swapping in a real local
  model later without touching the pipeline.
- **worker demo command** doubles as the fixture-driven full-pipeline test entry point.
