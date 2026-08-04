# Phase 8 — Competitor Diagnosis — COMPLETE ✅

## Deliverables
- **Canonical enums** (3 new, parity-tested across json/py/ts): `collection_status`,
  `collection_item_status`, `sample_presence`.
- **Three-competitor cap** — entity creation now rejects a 4th competitor per project (409,
  spec §5.2 / acceptance criterion 1); the existing comparison-rationale requirement is retained.
- **Models + migration `0008`**: `competitor_collections` (manifest: requested/collected/blocked/
  failed counts, duplicate rate, channels, period), `competitor_collection_items` (per-URL
  collected/blocked/failed — nothing silently dropped), `competitor_diagnoses` (limitation banner,
  sample sufficiency, serialized audits), `competitor_findings` (presence, finding_status,
  `is_public_proxy`, evidence spans).
- **Collection + diagnosis engine** (`app/services/competitor.py`) — deterministic, evidence-only:
  - **Sample manifests / limited collection** — ingests provided public text as `competitor_public`
    sources; blocked/failed URLs make the manifest **partial**, never complete; duplicate rate
    computed from canonical vs collected (reposts don't inflate coverage, §16.2).
  - **Sample-sufficiency** (§16.4) — piece-count bands (`<15/15–39/40+`) then modifiers; a
    **single-channel sample can never reach `high`** and high duplication downgrades — raw volume
    alone never wins.
  - **Content cards**, **public-evidence limitation banner** on every diagnosis (§15.1).
  - **Presence checklist** — each topic is `found` or **`not_found_in_sample`**, phrased
    "No evidence of X was found in the analyzed public sample" — never "does not do X" (§6.3).
  - **Audience/positioning** → `inference` (never observed_fact, §15.3); **public claim stays a
    claim** (`brand_claim`, never promoted from public evidence); **authority maturity** =
    public proxies only ("not owner readiness", §15.4); **VoC leak map** from public
    complaints/switching/questions; **performance** = public proxies only, `has_direct_outcome`
    always false — commercial performance is never inferred (§15.6).
  - Hard invariant: **no competitor finding is ever `observed_fact`**.
- **API** (`app/api/competitor.py`, wired): collect, list collections, run diagnosis, list, get.
- **UI** (`frontend/src/pages/CompetitorDiagnosis.tsx`): banner first, sample sufficiency + manifest
  status, presence list, and an observable-only findings table.

## Tests run (offline, no key)
```
backend:  uv run pytest -q            → 80 passed  (Phase 0–7 carried + Phase 8 below)
          - sample sufficiency: volume alone is not 'high'; single channel capped; 0 → insufficient
          - comparison-rationale required (422); max three competitors (4th → 409) [GATE]
          - blocked website → partial completion; collected/blocked/failed all recorded [GATE]
          - unequal sample comparison: 100-piece single-channel ≠ high; 20-piece two-channel = medium [GATE]
          - no definitive absence claim: pricing → not_found_in_sample, correct phrasing, no "does not" [GATE]
          - no inferred commercial performance: revenue record → proxy-only, no direct outcome [GATE]
          - public claim remains a claim; banner present; audience=inference; NO observed_fact [GATE]
backend:  ruff check + format         → All checks passed
          alembic upgrade→downgrade→upgrade (0001–0008)  → passes
frontend: enum parity / typecheck / build → 3 parity tests pass; production build succeeds
```

## Acceptance gate — PASS
The tool diagnoses up to three competitors from public samples without presenting private or
internal conclusions as facts:
- ✅ Up to three competitors; each requires a comparison rationale.
- ✅ Public-evidence limitation banner on every competitor diagnosis.
- ✅ Absence is `not_found_in_sample` with "no evidence in the analyzed public sample" — never a
  definitive "does not do X".
- ✅ Public claims stay claims; audience/positioning is inference; **no finding is an observed
  fact**; commercial performance is never inferred from public proxies.
- ✅ Unequal samples are compared by sufficiency, not raw volume.

## Next
Phase 9 — Comparative Coverage and Gap Engine: coverage cells/matrix, competitive-deficit and
white-space rules, gated gap candidates that still require evidence + review.
