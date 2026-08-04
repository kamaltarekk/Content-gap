# Domain Vocabulary

Frozen method reference for the Evidence-Based Content Diagnosis & Competitive Gap Analysis
MVP. The **canonical enum registry** is `docs/schemas/enums.json`; backend
(`backend/app/core/enums.py`) and frontend (`frontend/src/types/enums.ts`) are tested for exact
parity against it. Do not invent enum variants. Do not silently change diagnostic meaning —
record proposed changes in `docs/architecture-decisions/` and stop for approval.

## What the tool answers
1. What is wrong, missing, weak, misaligned, or unproven in the brand's current content?
2. Which parts of the buying decision, journey, customer language, and persuasion system are not
   adequately covered?
3. How does the brand compare with competitors **based only on the public/uploaded evidence
   actually collected**?
4. Which apparent content problems are really business, product, operational, sales, evidence,
   distribution, or measurement problems?
5. Is the project ready for content strategy, conditionally ready, blocked by missing evidence, or
   blocked by a non-content problem?

## Core thesis — what a valid gap is
> An informational, persuasive, trust, behavioral, or availability need connected to the target
> buying decision, supported by sufficient evidence, that the brand does not cover at the required
> depth, proof level, format, journey stage, or touchpoint.

A competitor publishing a topic the brand did not is **not** by itself a valid gap.

## Status vocabulary (must stay distinct)
- **finding_status** — epistemic status of a statement: `observed_fact`, `brand_claim`,
  `inference`, `hypothesis`, `unknown`. Facts, brand claims, inferences, hypotheses, and unknowns
  are never merged.
- **confidence_level** — `high | medium | low | insufficient_evidence`. How well evidence supports
  the statement. **Never** a decimal "probability".
- **severity_level** — `critical | high | medium | low`. Business importance. Always separate from
  confidence: a finding can be `critical` severity and `low` confidence simultaneously.
- **gap_status** — lifecycle of a gap candidate: `candidate → probable → confirmed`, or
  `rejected | insufficient_evidence | not_applicable | non_content_blocker`.
- **review_status** — human decision: `pending | approved | rejected | needs_changes |
  auto_accepted`.
- **classification_origin** — provenance: `deterministic | ai_proposed | human_assigned |
  imported`. AI proposals and human decisions are stored separately; a human edit never
  overwrites the AI proposal record.

## Entity rule
The **brand** may be diagnosed with internal and public evidence. A **competitor** may be
diagnosed **only** with the public or uploaded evidence collected. Never write "the competitor
does not do X" — write "No evidence of X was found in the analyzed public sample." Missing data is
not negative evidence.

## Evidence, not opinion
AI output is never evidence. The model extracts, classifies, and explains evidence that already
exists as `evidence_spans`. Every model classification must reference evidence IDs from the
supplied manifest; unknown IDs are rejected (`docs/methodology/evidence-rules.md`).

## Enum groups (see enums.json for members)
Core statuses: finding_status, confidence_level, severity_level, review_status, job_status,
analysis_status. Context: purchase_type, primary_bottleneck, entity_type, competitor_type.
Journey: journey_stage, content_layer, micro_decision_type. Buying group: buying_group_role.
Content/source: source_type, source_category, content_format, language_code, extraction_quality.
Persuasion: sales_element. Claims: claim_type, claim_proof_status, proof_type. Gaps: gap_status,
root_cause_type, gap_type. Evidence: evidence_role, classification_origin. VoC: bank_type.
Performance: paid_organic_status. Analysis: analysis_type.
