# Phase 5 — Content Classification — COMPLETE ✅

## Deliverables
- **AI provider abstraction** (`app/ai/provider.py`, spec §20.4): `AIProvider` protocol with
  `count_tokens` + `structured_generate`. The domain layer never imports the Anthropic SDK.
- **Deterministic fake provider** (`app/ai/fake_provider.py`): offline, bilingual heuristics; cites
  only supplied evidence ids; detects and **reports** injected instructions but never obeys them.
- **Anthropic adapter** (`app/ai/anthropic_provider.py`): system/preamble separated from delimited
  untrusted source; forces one JSON object; no non-default sampling params for claude-sonnet-5.
- **Structured-output schemas** (`app/ai/schemas.py`): strict Pydantic `ContentPieceClassification
  Result` (const schema_name, closed enums per dimension, 0–10 bounds, ≥1 evidence id).
- **Validation + one repair** (`app/ai/validate.py`): strict parse → **closed enums** →
  **unknown-evidence-id guard**; one controlled repair attempt; still-invalid → `needs_review`,
  **never persisted as approved**.
- **Prompt registry** (`app/ai/prompt_registry.py` + `prompts/content_piece_classification/v1.md`):
  versioned prompt with purpose/allowed-evidence/prohibited-inference/Arabic/competitor/injection
  sections + injection-guard system preamble.
- **Classification service** (`app/services/classify.py`): fingerprint = hash(content_hash +
  context_version + prompt_version + model + schema_version); **cache hit** on match; persists one
  row per dimension with `origin=ai_proposed`, confidence, evidence ids, review status
  (high-confidence auto-accept, else pending); supersedes prior current rows (**history preserved**).
- **Token counting + cost estimate** (`app/ai/estimate_cost_usd`, configurable pricing).
- **Classification jobs** (`classify_content` handler reusing Phase 4), **review queue**, single +
  **batch approval**, **classification history** — API `app/api/classification.py` (§11.13) + a
  review UI (`frontend/src/pages/Review.tsx`). Migration `0005`.

## Tests run (offline, fake provider, no key)
```
backend:  uv run pytest -q            → 51 passed  (Phase 0–4 carried + Phase 5 below)
          - invalid enum rejected; missing evidence id rejected; empty evidence id rejected
          - classify persists valid evidence + origin=ai_proposed + confidence + review status
          - INVALID output never persisted (rogue evidence id → needs_review, 0 rows) [GATE]
          - prompt injection reported, not obeyed (classification unchanged)
          - mixed-language classification (ar_en_mixed)
          - cache fingerprint prevents re-classify (2nd call = cache_hit, same rows)
          - human edit preserves AI proposal (proposed_value intact, approved_value separate)
          - estimate + run endpoints
backend:  ruff check + format         → All checks passed
frontend: typecheck / build           → clean; production build succeeds
```

## Acceptance gate — PASS
- ✅ Every persisted classification has valid evidence ids (⊂ the piece's spans), a confidence, an
  origin, and a review status.
- ✅ Invalid structured output never becomes an approved result — schema/enum/unknown-id failures
  (after one repair) route to `needs_review` and persist nothing.

## Next
Phase 6 — Voice of Customer, Claims, and Performance: VoC extraction + language banks (verbatim,
3-occurrence pattern, 10-phrase high-confidence threshold), claim + proof extraction (unsupported/
contradicted), performance import + validation with proxy labeling and incompatible-period
warnings. Gate: VoC/claims/proof/performance stay traceable and cannot be promoted from proxy/claim
to fact without evidence.
