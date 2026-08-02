# COST_MODEL.md — Content Gap Intelligence v0

> Provider prices are **not** hard-coded in source. They are read from environment
> (`PRICE_LLM_INPUT_PER_MTOK`, `PRICE_LLM_OUTPUT_PER_MTOK`, `PRICE_EMBEDDING_PER_MTOK`) and
> stored per usage event. The numbers below are **illustrative planning assumptions** you set
> to match your provider's current price sheet — verify before relying on them.

## What is instrumented (per run, persisted in `usage_events` + `analysis_runs.usage_json`)
Pages crawled · bytes stored · chunks generated · embedding operations · LLM calls ·
input tokens · output tokens · estimated provider cost · cost per pipeline stage ·
cost per published gap · cost per project per month.

## Assumptions (edit to taste)
- LLM input price: `PRICE_LLM_INPUT_PER_MTOK` (example: $3.00 / 1M tokens)
- LLM output price: `PRICE_LLM_OUTPUT_PER_MTOK` (example: $15.00 / 1M tokens)
- Embeddings: local deterministic provider → **$0** (`PRICE_EMBEDDING_PER_MTOK=0`)
- Extraction is the dominant LLM cost: ~1 call per content unit; coverage classification is
  shortlisted (top-k retrieval), not full-corpus; candidate generation + critique are bounded.
- Chunk size ≈ 900 tokens; extraction prompt overhead ≈ 700 tokens/unit; output ≈ 400 tokens/unit.

## Scenarios (illustrative, example prices above)
| Scenario | Content units | Weekly LLM calls | Input tok | Output tok | Est. weekly LLM $ |
|----------|---------------|------------------|-----------|------------|-------------------|
| Low      | 25            | ~40              | ~120k     | ~30k       | ~$0.81            |
| Expected | 60 (demo-scale× real) | ~110    | ~350k     | ~90k       | ~$2.40            |
| High     | 150           | ~300             | ~1.1M     | ~260k      | ~$7.20            |

Embeddings add $0 (local). Storage is small (normalized text + 384-float vectors).
Weekly refresh only reprocesses **changed** sources (content-hash gated), so steady-state cost
after the first run is typically a fraction of the initial run.

## Main cost drivers
1. Number of content units (owned + competitor) requiring extraction.
2. Re-extraction frequency — mitigated by hash-gated snapshots (unchanged ⇒ skipped).
3. Coverage classification breadth — mitigated by top-k semantic shortlist.
4. Output verbosity of candidate/critique — bounded by max field lengths + result cap of 10.

## Cost-control mechanisms (implemented)
- Hash-gated snapshots: no new snapshot / no reprocessing when content is unchanged.
- Top-k retrieval before any coverage LLM call — never send the full corpus in one prompt.
- Hard per-run caps: `LIMIT_MAX_CHUNKS_PER_RUN`, `LIMIT_MAX_TOKENS_PER_RUN`.
- Weekly cost budget: `LIMIT_WEEKLY_COST_BUDGET_USD` — exceeding it pauses the job and records
  a clear error (jobs never silently truncate evidence).
- Published gaps capped at 10; the rest go to the shadow sample (no extra LLM spend).
- `LLM_PROVIDER=fake` for local demo/CI ⇒ $0 and deterministic.

## Cost per published gap
`analysis_runs.usage_json` divides run cost by published-gap count. With the expected scenario
and example prices, ~$2.40 / (≤10 gaps) ⇒ roughly $0.24–$2.40 per published gap depending on
how many survive verification — surface this to the user rather than assuming a fixed value.
