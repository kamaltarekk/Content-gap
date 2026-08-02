# ARCHITECTURE.md — Content Gap Intelligence v0

## Components
```
┌──────────────┐     project token      ┌───────────────┐
│  Extension   │ ─────────────────────► │               │
│ (WXT/MV3     │   capture / read gaps  │   API         │
│  Side Panel) │ ◄───────────────────── │  (Fastify)    │
└──────────────┘                        │  /api/v1      │
                                        │               │
┌──────────────┐   REST + TanStack Q    │   - auth      │──┐
│  Web (Vite)  │ ◄────────────────────► │   - Zod       │  │ enqueue jobs
│  Dashboard   │                        │   - OpenAPI   │  │ (pg-boss)
└──────────────┘                        └──────┬────────┘  │
                                               │           ▼
                              ┌────────────────┴───────┐  ┌──────────────┐
                              │       PostgreSQL        │  │   Worker      │
                              │  + pgvector (embeddings)│◄─┤  (pg-boss)    │
                              │  + pg-boss (jobs/cron)  │  │  pipeline +   │
                              └─────────────────────────┘  │  weekly cron  │
                                                           └──────┬───────┘
                                        ┌─────────────────────────┘
                                        ▼
                               ┌──────────────────┐   ┌──────────────┐
                               │   @cgi/crawler   │   │   @cgi/llm    │
                               │  fetch/readability│   │ fake|anthropic│
                               │  cheerio/robots   │   │ + local embed │
                               └──────────────────┘   └──────────────┘
```
One PostgreSQL instance backs application data, vectors (pgvector), and the job/cron
system (pg-boss). No Redis, no separate vector DB, no graph DB.

## Data flow (one observable pipeline)
```
Ingestion → Normalization → Chunking → Structured Extraction → Semantic Deduplication
→ Required Decision-Support Map → Current Coverage Matrix → Candidate Gap Generation
→ Evidence Verification → Candidate Rejection/Critique → Transparent Prioritization
→ Report Publication (max 10)
```
Each stage has typed input/output, writes structured (Pino) logs, records failure state,
stamps `pipelineVersion`, and is idempotent/resumable at the run level. Stages never silently
swallow errors — failures are recorded on the `analysis_runs` row and per-source.

Triggers: (a) ingestion of a new/changed source auto-enqueues analysis; (b) the weekly
scheduler re-fetches URL sources, diffs content hashes, and reprocesses only changed material.
There is no manual "Run Analysis" control in the normal UI.

## Pipeline stages (files: `packages/analysis-engine/src/stages/*`)
| Stage | Kind | Responsibility |
|-------|------|----------------|
| ingestion | deterministic | pull raw content from sources → snapshots (hash-gated) |
| normalization | deterministic | Readability/Cheerio → clean text + metadata |
| chunking | deterministic | offset-accurate chunks + local embeddings |
| extraction | **LLM** | signals/cohort/journey mapping, chunk-grounded |
| dedup | deterministic + embed | exact-hash + semantic near-dup collapse |
| decision-support map | LLM (brief/cohort/VoC only) | required needs per cohort×stage |
| coverage matrix | retrieval + LLM classify | shortlist owned assets, classify coverage |
| candidate generation | LLM | candidate gaps from structured inputs |
| evidence verification | **deterministic** | exact-substring + offset + ID existence checks |
| critique/rejection | LLM (bounded) + deterministic | catch obvious errors; downgrade/reject |
| prioritization | **deterministic** | integer heuristic, stored components, labels |
| publication | deterministic | cap at 10; shadow-sample the rest |

## Deterministic vs LLM boundary
- **Deterministic:** URL normalization, content hashing, source ownership, file parsing,
  HTML extraction, exact-hash dedup, date parsing, quote-offset validation, evidence existence,
  priority formula, thresholds, status transitions, scheduling, retry policy, usage tracking,
  API auth, result caps, shadow-sample selection.
- **LLM:** signal extraction, cohort/journey mapping, question/objection/belief/proof/decision
  identification, semantic need comparison, candidate gap generation, coverage summaries,
  commercial-consequence explanation, content-role/asset-type recommendation, bounded critique.
- The LLM never selects URLs, executes tools, or reads credentials. Its output is always
  Zod-validated and ID-checked against the exact inputs it was given.

## Extension ↔ backend responsibilities
- **Extension:** hold backend URL + project token (in `chrome.storage.local`), capture the
  current page on explicit user action, submit to `/sources/capture`, read gaps/source status.
  No secrets, no silent capture, no history scraping.
- **Backend:** owns the Anthropic key, all analysis, all persistence, all scheduling.

## Security boundaries
- Project-scoped bearer tokens, SHA-256 hashed at rest, checked in constant time.
- Source content is untrusted: wrapped in delimiters, declared evidence-only, never executed.
- All model output validated; unknown-ID references rejected; injection fixtures tested.
- Crawler respects robots.txt, rate-limits per domain, never bypasses auth/CAPTCHA/paywalls.
