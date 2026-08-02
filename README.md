# Content Gap Intelligence — v0

An automated, evidence-verified content-gap detector for marketing teams. It ingests a business
brief, owned content, voice-of-customer data, and up to three competitors; builds a coverage
matrix; detects content gaps; **verifies every gap against exact source quotes**; ranks them with
a transparent heuristic; and shows at most the ten highest-priority gaps.

This is a **v0 experiment** to test one hypothesis:

> An automated system can identify content gaps that experienced marketers consider commercially
> relevant, evidence-backed, non-duplicative, and actionable.

It operates automatically but **never claims autonomous certainty or ground truth**. Priority is a
documented heuristic — not a confidence score. Evidence status is a rule outcome — not a probability.

## What it is (and is not)
- One **observable pipeline** (not 13 agents): Ingestion → Normalization → Chunking → Extraction →
  Semantic Dedup → Decision-Support Map → Coverage Matrix → Candidate Generation → Evidence
  Verification → Critique/Rejection → Prioritization → Publication.
- **Deterministic code** owns URL/hash/parse/offset/priority/threshold/scheduling/auth/limits.
  The **LLM** only extracts, maps, compares, drafts candidates, and does a bounded critique — its
  output is always Zod-validated and checked so it can only cite IDs it was given.
- Runs fully offline with a **deterministic fake LLM** and a **local multilingual embedding**
  provider (Arabic + English + mixed), so the demo and the whole test suite need **no API key**.
- Excludes (by design): ChatGPT capture/scraping, Gmail/CRM/WhatsApp/ad/analytics integrations,
  authenticated scraping, auto-publishing, multi-tenant, autonomous discovery, image/video
  understanding, separate graph/vector DB, `<all_urls>` permissions.

## Architecture
See `ARCHITECTURE.md`. Monorepo (pnpm + turbo):

```
apps/
  api/         Fastify /api/v1 (auth, Zod, OpenAPI); auto-triggers analysis on ingestion
  worker/      pg-boss consumer + weekly refresh scheduler; `pnpm demo` entry
  web/         React + Vite dashboard (wizard, gaps, coverage, evaluation, shadow, runs)
  extension/   WXT MV3 Chrome Side Panel (connection, capture, gaps, source status)
packages/
  shared/          enums, Zod schemas, deterministic helpers, priority + evidence rules, config
  database/        Drizzle schema, SQL migrations, pgvector, seed
  analysis-engine/ the pipeline + evidence verification + shadow sampling + ingestion
  llm/             provider interface, fake + Anthropic providers, local embeddings, injection defenses
  crawler/         fetch → Readability/Cheerio, robots.txt, rate limiting, file/sitemap parsers
  test-fixtures/   synthetic bilingual demo dataset
```

## Prerequisites
- Node.js 22+, pnpm 10+
- PostgreSQL 16 with the **pgvector** extension. `docker-compose.yml` provides this on host port
  **5433**. (If Docker is unavailable, any local Postgres 16 with `CREATE EXTENSION vector` works —
  point `DATABASE_URL` at it.)

## Install & set up
```bash
pnpm install
cp .env.example .env          # defaults already target the demo DB; no API key needed

# Start Postgres + pgvector (host port 5433)
pnpm db:up                    # docker compose up -d db
# ...or use an existing Postgres 16 and set DATABASE_URL

pnpm db:migrate               # apply migrations (creates the vector extension + tables)
```

## Run the fake demo (no Anthropic key)
Seeds the synthetic bilingual project and runs the **entire pipeline** with deterministic fake
providers, printing up to ten evidence-verified gaps and a project token for the extension:
```bash
pnpm demo
```
Expected: `publishedGaps=10 (cap 10)`, a `STRONG_EVIDENCE` gap for the implementation-complexity
objection, Arabic and English gaps, each with verified exact-quote evidence, and the embedded
prompt-injection attempt ignored (reported, never obeyed).

## Run the system locally
```bash
# 1) API (http://localhost:3001, docs at /docs, spec at /openapi.json)
pnpm --filter @cgi/api dev

# 2) Worker (consumes analysis jobs + weekly refresh; runs even when the extension is closed)
pnpm --filter @cgi/worker dev

# 3) Web dashboard (http://localhost:5173)
pnpm --filter @cgi/web dev
```
There is intentionally **no "Run Analysis" button** — analysis is triggered automatically by
ingestion events and the weekly scheduler.

## Load the Chrome extension
```bash
pnpm --filter @cgi/extension build      # outputs apps/extension/.output/chrome-mv3
```
Then in Chrome: `chrome://extensions` → enable **Developer mode** → **Load unpacked** →
select `apps/extension/.output/chrome-mv3`. Open the side panel, enter the backend URL
(`http://localhost:3001`) and a **project token** (printed by `pnpm demo`, or created via
`POST /api/v1/tokens`), click **Test connection**, then use **Capture current page**. The
extension never holds the Anthropic key — only the backend URL and the project token.

## Configure the real Anthropic provider
Set in `.env` (backend only — never in the extension):
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5
```
Restart the API and worker. Provider pricing is configured (not hard-coded) via
`PRICE_LLM_INPUT_PER_MTOK` / `PRICE_LLM_OUTPUT_PER_MTOK`; see `COST_MODEL.md`.

## Commands
```bash
pnpm test          # unit + integration (Vitest); fake providers, needs the local Postgres, no external API
pnpm typecheck     # tsc --noEmit across the workspace
pnpm build         # production builds (API/worker via tsup, web via vite, extension via wxt)
pnpm db:seed       # seed the demo project only
pnpm demo          # migrate + seed + full pipeline, prints gaps + a project token
```
Weekly refresh can be exercised in tests via `refreshProject(...)` with an injected fetch (see
`apps/worker/src/refresh.ts`) — unchanged content is not reprocessed; changed content is.

## Data-safety & legal
You must have the right to process any VoC data you upload (the dashboard shows this disclaimer).
The crawler respects robots.txt, rate-limits per domain, uses a descriptive user agent, and never
bypasses authentication, CAPTCHAs, paywalls, or access controls. Project/source/snapshot deletion,
token revocation, and configurable retention are provided. See `RISK_REGISTER.md`.

## Known limitations (v0)
- The **fake** LLM is heuristic (deterministic keyword/near-match), tuned to make the offline demo
  and tests hermetic. Real extraction quality comes from the Anthropic provider.
- The **local embedding** is a deterministic char-n-gram hash (no downloaded model). The provider
  interface allows swapping a real local model without touching the pipeline.
- Playwright is an opt-in fallback for JS-rendered public pages (`CRAWLER_PLAYWRIGHT_FALLBACK=true`);
  the demo and tests never require it.
- Single project, two cohorts, one offer, three competitors — the documented v0 limits.

## Documents
`IMPLEMENTATION_PLAN.md` · `ARCHITECTURE.md` · `COST_MODEL.md` · `RISK_REGISTER.md` · `CLAUDE.md` ·
generated `docs/openapi.json`.
