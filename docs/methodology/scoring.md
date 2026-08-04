# Scoring Methodology

All formulas are **initial configurable methodology, not universal truth** (spec §16). The
`rule_version` and weights are stored with every analysis run so prior reports stay reproducible
when weights change. Severity and confidence are computed and stored **separately** and never
collapsed into one number.

## Coverage score (0–10) — per entity × dimension × relevant touchpoint (§16.1)
| Component | Range |
|---|---:|
| Presence | 0–2 |
| Relevance to target decision | 0–2 |
| Depth and completeness | 0–2 |
| Proof quality | 0–2 |
| Touchpoint availability | 0–1 |
| Micro-decision / CTA support | 0–1 |
| **Total** | **0–10** |

Component anchors: **Presence** 0 none / 1 isolated mention / 2 repeated dedicated coverage;
**Relevance** 0 unrelated / 1 indirect / 2 directly supports the decision; **Depth** 0 label only /
1 partial / 2 complete with conditions & reasons; **Proof** 0 none / 1 weak-or-testimonial-only /
2 direct credible proof; **Touchpoint** 0 wrong/hard-to-find / 1 available where needed;
**Micro-decision** 0 no help / 1 clearly helps decide or act.

Rules (§16.2): score only from approved content + evidence; frequency may raise presence
*confidence* but cannot exceed the presence component; excluded reposts do not raise score;
contradictory content lowers confidence and can create a contradiction finding; every score
carries `evidence_ids` and `reasoning`.

## Competitive deficit candidate (§16.3)
```
brand coverage < 5 AND strongest comparable competitor coverage > 7
AND both evaluated at the same bottleneck-relevant touchpoint / equivalent stage
```
This creates a **candidate only** — it must still pass need relevance, sample sufficiency, and
evidence review.

## Sample sufficiency (§16.4) — computed per entity
Piece-count bands: `<15` low, `15–39` medium, `≥40` high. Then modified by channel
representation, time-window completeness, duplicate rate, extraction quality, and relevant-piece
count. Final output ∈ `{high, medium, low, insufficient_evidence}`. **Piece count alone cannot
produce high confidence.**

## Content readiness scorecard (§16.5) — 0–10 per dimension
Expert/author availability, evidence availability, story inventory, product/service knowledge,
VoC availability, production-capacity realism, claim governance, measurement readiness. Convert to
an A–D grade **only after** showing the dimension scores and evidence. Do not infer founder
willingness from public posting frequency.

## Severity score (0–100) (§18.1)
| Dimension (each 0–10) | Weight |
|---|---:|
| Impact on target buying decision | 30% |
| Relevance to primary bottleneck | 25% |
| Journey / micro-decision criticality | 20% |
| Current coverage deficiency | 15% |
| Commercial relevance | 10% |

Labels: Critical 80–100 · High 65–79.99 · Medium 45–64.99 · Low 0–44.99.

## Confidence score (0–100) (§18.2)
| Dimension | Weight |
|---|---:|
| Direct VoC / customer evidence | 25% |
| Evidence diversity and traceability | 20% |
| Sample sufficiency | 20% |
| Performance / behavioral evidence | 15% |
| Human validation | 20% |

Labels: High 75–100 · Medium 50–74.99 · Low 25–49.99 · Insufficient <25.

## Confidence caps (§18.3) — applied deterministically after scoring
- Competitor strategy/audience inference without explicit statement → max `medium`.
- Competitor internal performance inference → prohibited; status stays `unknown`.
- Gap based only on competitor publishing behavior → max `low`.
- Gap without any direct customer/journey evidence → max `medium`.
- Critical finding without human approval → cannot become `confirmed`.
- Unreadable/low-quality source evidence reduces the related confidence component.

## Fingerprints (§20.10)
- **Classification fingerprint** = hash(content_hash + context_version_id + prompt_version +
  model_id + schema_version).
- **Analysis fingerprint** = hash(dataset_snapshot_id + context_version_id + model_id +
  prompt_manifest_version + rule_version + parser_version_manifest).
A matching fingerprint returns the cached result unless the user forces a refresh. Incrementing
any version component creates a **new** run rather than a cache hit (spec §6.30).
