# Phase 6 — Voice of Customer, Claims, and Performance — COMPLETE ✅

## Deliverables
- **Domain models** (`app/db/models/voc.py`): `VocEntry` (verbatim phrase stored EXACTLY,
  `pattern_key`, `occurrence_count`, non-null `evidence_span_id`), `Claim` (`proof_status`
  default `unsupported`, `finding_status` default `brand_claim`), `ClaimEvidence` (composite PK
  `claim_id`+`evidence_span_id`, `proof_type`, `evidence_role`, 0–10 `quality_score` CHECK),
  `PerformanceRecord` (`metric_name`, `paid_organic_status`, `is_proxy`, period bounds, spend,
  audience size). Migration `0006`.
- **VoC service** (`app/services/voc_claims.py`):
  - `add_voc_entry` — ingests every phrase as a traceable `customer_voice` source + evidence span;
    the phrase is stored **byte-for-byte, never rewritten or transliterated** (spec §4.6). Repetition
    detection sets `pattern_key = sha256(normalize_for_hash(phrase))` and keeps every sibling row's
    `occurrence_count` equal to the pattern total.
  - `language_banks` — a pattern is **confirmed** once it repeats `voc_pattern_confirm_min` (3)
    times; a bank reaches **high confidence** only with `voc_high_confidence_min_phrases` (10)
    **approved** phrases (spec §10.13). Both thresholds are configuration, not hard-coded.
- **Claims & proof** (`app/services/voc_claims.py`):
  - A claim starts **`unsupported`**. `attach_claim_evidence` recomputes proof deterministically:
    any `contradicts` → **`contradicted`**; no `supports` → `unsupported`; a high-quality (≥7),
    non-proxy `supports` → `proven`; otherwise `partially_proven`.
  - `promote_claim_finding_status` is **the gate**: promotion to `observed_fact` raises
    `ClaimPromotionError` (HTTP 422) unless supporting evidence exists — a claim cannot become a
    fact without evidence (spec §4.20).
- **Performance** (`app/services/voc_claims.py`): `metric_is_proxy` marks visible-engagement and
  **all unknown** metrics as proxies; direct commercial outcomes (conversions/revenue/sales/…)
  are not proxies (spec §6.21). `performance_validation` warns on **paid+organic mixed** for the
  same metric and **incompatible periods** (same metric across different windows) — never silently
  aggregated.
- **API** (`app/api/voc.py`, wired into `app/main.py`): VoC manual add / list / approve /
  language-banks; claim create / attach-evidence / promote / list; performance manual / list /
  validation.
- **UI** (`frontend/src/pages/Voc.tsx`): add a verbatim phrase, approve it, and read the language
  banks whose confidence rises only after enough real phrases are approved.

## Tests run (offline, fake provider, no key)
```
backend:  uv run pytest -q            → 59 passed  (Phase 0–5 carried + Phase 6 below)
          - VoC phrase stored verbatim (Arabic round-trips byte-for-byte) [GATE]
          - 3 identical phrases → occurrence_count=3, pattern confirmed
          - language bank high-confidence only at 10 approved phrases (low until approved)
          - claim starts unsupported; cannot promote to observed_fact without evidence → 422 [GATE]
          - claim promotes to fact once supported by high-quality evidence (proof_status=proven)
          - contradictory evidence → proof_status=contradicted; promotion still refused
          - performance proxy classification (views/unknown=proxy, revenue=not proxy)
          - validation warns on paid+organic mixed and incompatible periods; paid/organic separated
backend:  ruff check + format         → All checks passed
frontend: typecheck / build / test    → clean; production build succeeds; 3 parity tests pass
```

## Acceptance gate — PASS
- ✅ VoC entries, claims, proof records, and performance records are each traceable to an evidence
  span / content piece.
- ✅ A claim cannot be promoted from claim to fact without supporting evidence (422); contradicted
  claims are never promotable.
- ✅ A performance metric cannot be promoted from proxy to fact — proxies (including unknown
  metrics) are labeled, and incompatible/paid-organic aggregation is warned, not silently merged.

## Next
Phase 7 — Brand Diagnosis: evidence-verified brand findings (severity and confidence kept
separate, never collapsed), gap candidates from the analyzed sample only.
