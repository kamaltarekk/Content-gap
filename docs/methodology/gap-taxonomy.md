# Gap Taxonomy

Gap detection turns needs + coverage + evidence into typed, status-tracked gaps. Every gap
carries separate `severity`/`confidence`, a `root_cause_type`, an `alternative_explanation`, and
evidence IDs. A critical gap cannot become `confirmed` without human approval.

## Gap candidate prerequisites (§17.1)
1. A defined customer need, question, objection, micro-decision, sales element, or journey
   requirement.
2. Connection to the target buying decision and primary segment.
3. Brand coverage below the required level, or coverage in the wrong format/touchpoint.
4. At least one evidence source, or an explicit `insufficient_evidence` status.

## gap_status lifecycle (§17.2)
- `candidate` — detected by a rule / AI assist; has not passed evidence + review gates.
- `probable` — relevant need, weak brand coverage, partial evidence, plausible impact; needs more
  validation.
- `confirmed` — connected to the decision, sufficient traceable evidence, inadequate brand
  coverage, no stronger alternative explanation, **and human approval**.
- `insufficient_evidence` — may matter, but evidence cannot support a reliable conclusion.
- `rejected` — irrelevant, already covered, unsupported, or better explained by another cause.
- `non_content_blocker` — cannot be solved by content until a business/product/operational/sales
  condition changes.

## Detection rules (initial, configurable)
- **Competitive deficit** (§16.3): brand `<5` and strongest comparable competitor `>7` at the same
  stage/touchpoint → candidate.
- **White space** (§17.3): need importance `≥7/10` AND brand coverage `<5` AND every analyzed
  competitor `<5` AND confidence ≥ medium. Human review must confirm a credible capability/proof
  path before the brand "owns" the territory.
- **Market saturation** (§17.4): most competitors cover it strongly, brand is similar/generic, low
  differentiation, and no evidence another generic piece would move the decision. Saturation is
  **not** a reason to skip a mandatory category-standard element (e.g. logistics, risk info).
- **False opportunity** (§17.5): competitors publish heavily but no VoC/journey/business/
  performance evidence supports importance, or it is off-decision/off-segment, or the coverage is
  promotional noise → `false_opportunity`.
- **Competitor leak** (§17.6): repeated customer complaint in competitor evidence + direct decision
  relevance + brand operational ability to solve + existing (or explicitly required) proof. If
  brand capability is unknown → a **research backlog item**, not a confirmed opportunity.
- **Non-content gap** (§17.7): e.g. no delivery SLA, undefined price/offer, unreliable
  availability, missing sales follow-up, broken checkout, claim conflicts with policy, no proof
  source. The tool must state what must change before content can credibly help.

## root_cause_type decision tree (§19.1)
```
Need / decision support missing?
  ├─ Information does not exist internally ............ knowledge_gap
  ├─ In people's heads but not documented ............ extraction_gap
  ├─ Claim exists but proof does not ................. evidence_gap
  ├─ Knowledge & proof exist but no content .......... coverage_gap
  ├─ Content exists but not at needed location ....... distribution_gap
  ├─ Content exists in unsuitable form ............... format_gap
  ├─ Content exists but unclear / shallow ............ quality_gap
  ├─ Outcome cannot be measured ...................... measurement_gap
  ├─ Offer / economics prevent credibility ........... business_gap
  ├─ Product capability missing ...................... product_gap
  ├─ Fulfilment / service cannot support promise ..... operational_gap
  └─ Sales process fails after content ............... sales_gap
```

## Alternative explanations (§18.4)
Every high/critical gap requires ≥1 plausible alternative explanation (weak distribution;
product/offer problem; sample excludes private sales content; content correct but hard to find;
incompatible performance denominator; segment-specific objection). A reviewer must explicitly
accept or reject it.

## No content generation in MVP (§19.3)
The engine may state a required information asset ("a documented cost comparison is missing"). It
must **not** produce campaign ideas, scripts, hooks, or calendars.
