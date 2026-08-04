# Phase 9 — Comparative Coverage and Gap Engine — COMPLETE ✅

## Deliverables
- **Models + migration `0009`**: `gap_analysis_runs` (pinned `rule_version` + weights so prior
  reports stay reproducible, §6.2/§16), `coverage_cells` (per entity × territory, the six §16.1
  components + score + evidence), `gaps` (separate severity/confidence **scores and labels**,
  root cause, `alternative_explanations`, `competitor_only_signal`, `requires_human_approval`,
  approval fields).
- **Gap engine** (`app/services/gap_engine.py`) — deterministic, evidence-first:
  - **Coverage cells & matrix** — six-component score (presence/relevance/depth/proof/touchpoint/
    micro-decision, 0–10) per entity × sales-element territory, each cell carrying evidence + a
    reasoning string.
  - **Core rules** — competitive deficit (`brand<5 ∧ strongest competitor>7` at the **same**
    territory → candidate), white space (`importance≥7 ∧ brand<5 ∧ all competitors<5`), saturation
    (`≥2 competitors>7 ∧ brand≥5`), false opportunity (competitor publishes but no customer
    importance), competitor leak (public competitor complaints), non-content gap (operational
    brand complaints).
  - **Severity (0–100)** and **confidence (0–100)** scored from the §18.1/§18.2 weighted
    dimensions, **kept fully separate**, with the §18.3 caps applied (competitor-only signal → max
    `low`; no direct customer/journey evidence → max `medium`).
  - **Root-cause engine** (§19.1 tree: evidence_gap / coverage_gap / quality_gap / operational_gap…)
    and **alternative explanations** attached to every high/critical gap (§18.4), each awaiting
    reviewer accept/reject.
  - **No auto-confirm** — the engine only emits candidate/probable/rejected/non_content_blocker; a
    critical gap reaches `confirmed` **only** through explicit human approval, which also credits
    the human-validation confidence component.
- **API** (`app/api/gap.py`, wired): run analysis, list runs, get run (matrix + gaps), approve gap.
- **UI** (`frontend/src/pages/GapExplorer.tsx`): gap table with **separate severity/confidence
  columns**, root cause, evidence + alternative-explanation counts, and an Approve action for gaps
  that require human sign-off.

## Tests run (offline, no key)
```
backend:  uv run pytest -q            → 91 passed  (Phase 0–8 carried + Phase 9 below)
          - coverage components: brand weak (4) vs competitor strong (10); pure formula
          - severity/confidence independent (critical severity with low confidence)
          - importance low without customer evidence
          - brand<5 & competitor>7 → competitive_coverage_gap candidate [GATE]
          - same-territory requirement: authority weakness not matched to comparison strength [GATE]
          - competitor-only signal → confidence capped low [GATE]
          - white-space fixture → market_white_space candidate [GATE]
          - false-opportunity fixture → false_opportunity rejected [GATE]
          - saturated territory fixture → market_saturation [GATE]
          - non-content gap fixture → non_content_gap / non_content_blocker / operational_gap [GATE]
          - every critical gap has evidence + alternative explanation; engine never auto-confirms;
            approval promotes to confirmed [GATE]
backend:  ruff check + format         → All checks passed
          alembic upgrade→downgrade→upgrade (0001–0009)  → passes
frontend: enum parity / typecheck / build → 3 parity tests pass; production build succeeds
```

## Acceptance gate — PASS
- ✅ Expected fixture gaps match gold-standard outcomes: each rule (deficit, white space,
  saturation, false opportunity, competitor leak, non-content) produces the correct
  `gap_type`/`gap_status`, root cause, and severity/confidence separation.
- ✅ No critical gap can be confirmed without human approval — the engine never emits `confirmed`;
  a critical gap carries `requires_human_approval=true` and only the approve endpoint confirms it.

## Next
Phase 10 — Reports and Strategy-Readiness Gate: executive diagnosis, evidence limitations, brand +
competitor sections, comparative matrix, gap register, root-cause map, research backlog, the
four-status readiness decision, version manifest, and JSON/CSV/print-PDF exports with snapshot
immutability.
