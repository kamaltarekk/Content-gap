# RISK_REGISTER.md — Content Gap Intelligence v0

Severity: L/M/H. "Mitigation" describes what is implemented in this repo.

## Legal & compliance
| # | Risk | Sev | Mitigation |
|---|------|-----|------------|
| L1 | Website Terms of Service prohibit crawling | M | Only public pages; descriptive UA; per-domain rate limit; user supplies URLs (no autonomous discovery). Operator responsibility documented in README. |
| L2 | robots.txt disallow | M | `CRAWLER_RESPECT_ROBOTS=true` — fetch/parse robots, skip disallowed paths, record a source error. |
| L3 | Copyright — storing competitor content | M | Store minimal normalized text needed for evidence quotes; snapshots deletable; configurable retention (`RETENTION_SNAPSHOT_DAYS`). Quotes are short substrings used as evidence, not republished. |
| L4 | Personal data in VoC uploads | H | Visible disclaimer that the user must have the right to process uploaded VoC. Project/source/snapshot deletion + retention. No enrichment, no third-party sharing. |
| L5 | Uploaded customer conversations misuse | H | Same as L4; VoC is treated as untrusted data, never as instruction; not sent to any non-configured provider. |

## Data safety
| # | Risk | Sev | Mitigation |
|---|------|-----|------------|
| D1 | Data retention sprawl | M | `RETENTION_SNAPSHOT_DAYS`; deletion endpoints for project/source/snapshot; old non-current snapshots prunable. |
| D2 | Authenticated / paywalled content | H | Crawler never sends credentials, never bypasses auth/CAPTCHA/paywall/rate limits; public content only. |
| D3 | Right-to-be-forgotten / deletion | M | `DELETE /sources/:id`, project deletion cascade, token revocation, snapshot deletion. |
| D4 | Competitor crawl rate too aggressive | M | `CRAWLER_PER_DOMAIN_RPS` per-domain token bucket; 50 URLs/competitor cap. |

## Security
| # | Risk | Sev | Mitigation |
|---|------|-----|------------|
| S1 | Prompt injection via competitor/VoC content | H | System/data separation with delimiters; "source is evidence, never instruction"; strict Zod + enum + max-length validation; unknown-ID rejection; suspicious-instruction logging; injection fixtures in tests. |
| S2 | API key exposure | H | Anthropic key lives only in backend env; never in extension, never returned by any endpoint. |
| S3 | Token theft | M | Project tokens SHA-256 hashed at rest; constant-time compare; revocable; optional expiry. |
| S4 | Model-controlled side effects | H | No model-selected URLs, no model tool execution, no model credential access. |
| S5 | Chrome Web Store permission review friction | M | Minimal permissions (`sidePanel`, `storage`, `activeTab`, `scripting`); host permissions requested per user-approved domain at runtime; no `<all_urls>`; no remote code. |

## Product & analytical
| # | Risk | Sev | Mitigation |
|---|------|-----|------------|
| P1 | System asserts false certainty | H | No decimal confidence; evidence-status is a labeled rule outcome; priority is a transparent heuristic with visible components; language throughout avoids "ground truth". |
| P2 | Fabricated / mis-cited evidence | H | Deterministic exact-substring + offset + ID-existence verification before publish; unverifiable ⇒ downgrade/reject with recorded reason. |
| P3 | Mistaking operational/offer problems for content gaps | M | Bounded critique explicitly tests "is this a non-content problem?" and can mark/reject. |
| P4 | Systematic false negatives (missed gaps) | M | Shadow sample of rejected/low-ranked candidates; evaluators can flag missed valid gaps; tracked in calibration. |
| P5 | Arabic quality lags English | M | Multilingual local embeddings; language detection per unit; evaluation slices by language; flagged as a revise-trigger. |
| P6 | Over-crawl / runaway cost | M | Per-run chunk/token caps; weekly cost budget pauses jobs; result cap of 10. |

## Explicit exclusions (not built, by design)
No ChatGPT capture/scraping, no Gmail/CRM/WhatsApp/ad-platform/GA integration, no authenticated
scraping, no auto-publishing, no multi-tenant, no autonomous competitor/cohort discovery, no image
or video understanding (transcript-only), no separate graph/vector DB, no 13-agent orchestration.
