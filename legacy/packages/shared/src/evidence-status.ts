import type { CoverageStatus, EvidenceRole, EvidenceStatus, OwnerType } from "./enums.js";

// Evidence status is an OPERATING CATEGORY produced by explicit rules — never a numeric
// confidence. The rule id + human explanation are exposed to the user.

export interface EvidenceInputItem {
  role: EvidenceRole;
  ownerType: OwnerType; // where the quote came from
  verified: boolean; // exact-substring + offset validated
}

export interface EvidenceStatusResult {
  status: EvidenceStatus;
  ruleId: string;
  explanation: string;
}

const FIRST_PARTY: OwnerType[] = ["BUSINESS_BRIEF", "VOC"];

/**
 * Deterministic classification. Coverage insufficiency means the owned coverage for the need
 * is one of NONE/MENTION_ONLY/WEAK/PARTIAL/OUTDATED/UNSUPPORTED (i.e. not STRONG).
 */
export function classifyEvidenceStatus(
  evidence: EvidenceInputItem[],
  ownedCoverage: CoverageStatus,
): EvidenceStatusResult {
  const verified = evidence.filter((e) => e.verified);
  const distinctSources = new Set(verified.map((e) => `${e.ownerType}:${e.role}`)).size;
  const hasFirstParty = verified.some((e) => FIRST_PARTY.includes(e.ownerType));
  const hasCustomerDemand = verified.some((e) => e.role === "CUSTOMER_DEMAND" || e.ownerType === "VOC");
  const onlyCompetitor = verified.length > 0 && verified.every((e) => e.ownerType === "COMPETITOR");
  const coverageInsufficient = ownedCoverage !== "STRONG";

  if (verified.length >= 2 && distinctSources >= 2 && hasFirstParty && coverageInsufficient) {
    return {
      status: "STRONG_EVIDENCE",
      ruleId: "STRONG.multi-independent-first-party",
      explanation:
        "Two or more independent verified evidence items, at least one first-party (strategy or VoC), and owned coverage is demonstrably insufficient.",
    };
  }

  if (verified.length === 0 || onlyCompetitor || !hasCustomerDemand) {
    return {
      status: "HYPOTHESIS",
      ruleId: "HYPOTHESIS.inference-or-competitor-only",
      explanation:
        "The idea rests on inference or mostly competitor context; direct first-party customer demand is not verified.",
    };
  }

  return {
    status: "PARTIAL_EVIDENCE",
    ruleId: "PARTIAL.single-or-indirect",
    explanation:
      "One credible verified evidence source, or indirect evidence, or ambiguous owned coverage.",
  };
}
