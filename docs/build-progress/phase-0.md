# Phase 0 — Freeze the Method — COMPLETE ✅

## Deliverables
### Step 1 — Methodology files & schemas
- `docs/methodology/domain-vocabulary.md`
- `docs/methodology/gap-taxonomy.md`
- `docs/methodology/scoring.md`
- `docs/methodology/evidence-rules.md`
- `docs/schemas/enums.json` — canonical enum registry (single source of truth, 31 enum groups)
- `docs/schemas/content_piece_classification_result.schema.json` (JSON Schema, from spec §13.2)
- `docs/schemas/evidence_extraction_result.schema.json`
- `docs/schemas/gap_candidate_explanation.schema.json`

### Step 2 — Enums & parity
- `backend/app/core/enums.py` — Python `str, Enum` for all 31 groups + `ENUM_REGISTRY`
- `frontend/src/types/enums.ts` — TS `const` arrays + union types + `ENUM_REGISTRY`
- Parity tests assert both sides match `docs/schemas/enums.json` exactly (names, members, order).

### Step 3 — Gold-standard fixture
- `fixtures/gold_standard/gold_standard.json` — Arabic-first Naqaa water-filter project:
  1 brand, 2 competitors, 16 content pieces (AR/EN/mixed), 6 VoC entries, 3 claims (incl. one
  `unsupported` and one `partially_proven`), and 5 expected gaps covering **confirmed**,
  **probable**, **false_opportunity (rejected)**, **market_white_space (candidate)**, and a
  **non_content_blocker** — each with resolvable evidence IDs and separate severity/confidence.

## Tests run
```
backend:  uv run pytest            → 9 passed
          - test_enum_parity.py (3): group names, members+order, no duplicates
          - test_gold_standard_fixture.py (6): evidence resolves, claim/context evidence resolves,
            severity≠confidence separateness, canonical enums, verbatim spans, spec minimums
frontend: pnpm test (vitest)       → 3 passed  (enum parity: names, members+order, no duplicates)
```

## Acceptance gate — PASS
- ✅ The project can be diagnosed manually using the same schemas (fixture is schema-shaped and
  validated).
- ✅ Every expected gap has evidence IDs (enforced by `test_every_expected_gap_has_resolvable_evidence`).
- ✅ Severity and confidence are separate (enforced by `test_severity_and_confidence_are_separate`;
  gap-01 is `high` severity / `medium` confidence).
- ✅ No unresolved enum or status ambiguity (all fixture enum fields validated against the frozen
  registry; 31 enum groups frozen).
- ✅ Backend and frontend enum parity test passes.

## Known limitations / notes
- JSON Schemas are authored for the three highest-value AI outputs; remaining prompt schemas
  (voc_extraction, claim_proof, competitor_signals, executive_report) are added in Phase 5 with
  their prompts. Recorded, not silently skipped.
- Environment deviations (Docker unavailable, PG16 vs 17) documented in
  `docs/architecture-decisions/0001-repo-placement-and-environment.md`.

## Next
Phase 1 — Foundation: FastAPI app, React/Vite app, Docker Compose (Postgres/Redis/MinIO),
SQLAlchemy + Alembic, auth modes, `/health/live` + `/health/ready`, tooling (ruff/mypy/pytest/
ESLint/Vitest), CI baseline.
