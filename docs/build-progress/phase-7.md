# Phase 7 — Brand Diagnosis — COMPLETE ✅

## Deliverables
- **Canonical enums** (5 new, in `docs/schemas/enums.json` + backend + frontend, parity-tested):
  `readiness_dimension`, `readiness_grade`, `brand_diagnosis_dimension`,
  `decision_alignment_label`, `performance_signal_type`.
- **Domain models** (`app/db/models/brand_diagnosis.py`, migration `0007`): `BrandDiagnosis`
  (grade, bottleneck, limitations, serialized audits), `BrandReadinessScore` (0–10 per dimension
  with rationale + cited evidence span, 0–10 CHECK), `BrandFinding` (**severity and confidence in
  separate columns**, finding_status, `is_non_content_blocker`, `evidence_span_ids` → clickable).
- **Diagnosis engine** (`app/services/brand_diagnosis.py`) — deterministic, evidence-driven, no AI:
  - **Content readiness scorecard** — 8 dimensions scored 0–10 with rationale; operational unknowns
    (`expert_author_availability`, `production_capacity_realism`) reported as
    `insufficient_evidence`, **not inferred from posting frequency** (spec §14.1). A–D grade is
    derived only from scorable dimensions and shown **after** the dimension scores (spec §16.5).
  - **Sales-elements audit** — all 17 elements scored via a transparent coverage formula
    (`min(10, 2 × aligned covering pieces)`), **filtered to the project's primary bottleneck**
    (spec §14.5).
  - **Decision-alignment audit** — pieces whose journey stage is `not_applicable` are labeled
    `not_aligned_with_current_decision`, **excluded from coverage and never penalized** (spec §14.2).
  - **Journey coverage**, **claim–proof integrity** (unsupported → high severity / low confidence;
    contradicted → critical), **performance-evidence quality** (signals categorized; a proxy-only
    library is flagged — conversion is never inferred from views, spec §14.7).
  - **Non-content blocker detection** — bilingual keyword seed over complaint/switching-reason VoC
    flags candidate blockers content cannot fix (spec §17.7), for human confirmation.
  - Global **limitations** on every diagnosis; **no strategy or recommendations are produced**.
- **API** (`app/api/brand_diagnosis.py`, wired): run diagnosis, list, get full payload.
- **UI** (`frontend/src/pages/BrandDiagnosis.tsx`): scorecard before grade, bottleneck-filtered
  element coverage, a findings table with **separate severity/confidence columns** and evidence
  counts, and the limitations banner.

## Tests run (offline, no key)
```
backend:  uv run pytest -q            → 72 passed  (Phase 0–6 carried + Phase 7 below)
          - coverage score formula (0,1,3,5,7 → 0,2,6,10,10 capped) [GATE]
          - 3 aligned pieces covering an element → coverage 6, with clickable evidence
          - bottleneck-filtered sales-element audit (persuasion set) [GATE]
          - not-aligned content labeled, excluded from coverage, finding severity=None [GATE]
          - unsupported claim → finding severity=high AND confidence=low (separate axes) [GATE]
          - non-content blocker fixture (Arabic delivery complaint) → traceable blocker [GATE]
          - scorecard has 8 dims, operational unknowns=insufficient_evidence, limitations present,
            and NO strategy/recommendation keys anywhere in the payload [GATE]
          - run requires a primary brand entity (422); bottleneck maps are valid sales elements
backend:  ruff check + format         → All checks passed
          alembic upgrade→downgrade→upgrade (0001–0007)  → passes
frontend: enum parity / typecheck / build → 3 parity tests pass; production build succeeds
```

## Acceptance gate — PASS
A real fixture produces a brand diagnosis with:
- ✅ **Clickable evidence** — readiness dimensions and findings carry real `evidence_span_id`s.
- ✅ **Limitations** — a global limitations statement plus per-finding "no evidence in the sample".
- ✅ **Separate severity/confidence** — stored and returned as distinct columns; an unsupported
  claim is simultaneously high severity and low confidence.
- ✅ **No strategy-generation output** — asserted: the payload contains none of
  recommendation/strategy/suggested_content/next_actions/action_plan/playbook/advice.

## Next
Phase 8 — Competitor Diagnosis: observable-only competitor analysis with the mandatory limitation
banner, public-proxy-only authority signals, audience status as inference/hypothesis (not
observed_fact), and "no evidence of X in the analyzed sample" phrasing.
