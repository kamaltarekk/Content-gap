# Phase 2 — Projects & Diagnostic Context — COMPLETE ✅

## Deliverables
- **Projects CRUD** (`app/api/projects.py`): create/list/get/patch, soft-delete + restore, summary.
- **Brand & competitor entities** (`app/api/entities.py`): create/list/get/patch/delete;
  exactly-one-primary-brand per project (DB partial unique index); a competitor requires a
  comparison rationale.
- **Buying-group roles** (`app/api/buying_group.py`): project-scoped CRUD, canonical role +
  display label.
- **Versioned diagnostic context** (`app/api/context.py`): create version, list, get, patch
  (pending only), **validate** (prerequisite gate), **approve** (immutable after), **clone**
  (clone-on-edit). Auto-incrementing `version_number` per project.
- **Precondition gate** (`app/rules/preconditions.py`): deterministic §8.3 / Gate 1 scope-validity
  check — required fields, ≥2 evidence refs per entered A/D/P score, channel + period scope; returns
  `can_run_full_analysis` / `can_run_partial_analysis` and warnings.
- **Audit log** (`app/core/audit.py` + `audit_log` table): create/update/approve/clone/delete
  recorded with actor, object, and metadata.
- **Migration `0002`**: projects, entities (+ one-primary-brand partial unique index, entity_type
  CHECK), diagnostic_context_versions (unique version, 1–10 score CHECKs), buying_group_roles,
  audit_log.
- **Context setup UI** (`frontend/src/pages/Setup.tsx` + HashRouter): Arabic-first (`dir="auto"`)
  flow that creates project → brand → context version → shows the prerequisite gate result.

## Tests run (offline, local Postgres :5433)
```
backend:  uv run pytest -q            → 25 passed  (Phase 0/1 carried + Phase 2 below)
          - one-primary-brand constraint → 409 ONE_PRIMARY_BRAND_PER_PROJECT
          - competitor requires comparison rationale → 422 then 201
          - missing-prerequisite response: validate → fail, lists brand_entity/included_channels/
            analysis_period_start; approve blocked → 422
          - approve → immutable (patch 409); clone-on-edit → new pending version, editable;
            original approved version unchanged
          - Arabic form persistence: project + context Arabic round-trips byte-for-byte
          - score-evidence rule (pure): score without ≥2 refs is blocked
          - migration upgrade/downgrade now spans 0001+0002
backend:  ruff check + ruff format    → All checks passed
frontend: pnpm typecheck / test / build → clean; 3 passed; production build succeeds
```

## Acceptance gate — PASS
- ✅ A user can create and approve a context version containing one buying decision, purchase
  type, segment, and bottleneck (verified end-to-end via the API).
- ✅ Full analysis remains **blocked** when required data is missing — the validate endpoint returns
  `can_run_full_analysis=false` with the exact missing fields, and `approve` is rejected (422) until
  the gate passes. Approved versions are immutable (edits require clone).

## Next
Phase 3 — Evidence System: file/manual/URL sources, immutable source snapshots, PDF/DOCX/TXT/MD/CSV
parsing with extraction quality + warnings, content-piece extraction, evidence spans (verbatim),
object storage, duplicate grouping, and source/content UI. Gate: open a content piece → view an
evidence span → navigate to the exact source snapshot/location; original and normalized text stay
separate.
