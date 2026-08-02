import {
  type AllowedIds,
  type CandidateGap,
  CandidateGapResponseSchema,
  type CoverageClassification,
  CoverageResponseSchema,
  CritiqueVerdictSchema,
  type DecisionSupportNeed,
  DecisionSupportResponseSchema,
  ExtractionResponseSchema,
} from "@cgi/shared";
import { detectInjection, detectJourneyStage, detectLanguage, detectSignals, matchCohort } from "./heuristics.js";
import type {
  CandidateInput,
  CoverageInput,
  CritiqueInput,
  DecisionSupportInput,
  ExtractionInput,
  LlmProvider,
  LlmResult,
} from "./types.js";
import { estimateTokens, validateResponse } from "./validate.js";

/**
 * Deterministic, offline LLM stand-in. Same input -> same output. It pattern-matches text
 * with the shared heuristics; it NEVER follows instructions embedded in source content
 * (those are only logged as suspiciousInstructions). Used for local demo + all tests.
 */
export class FakeLlmProvider implements LlmProvider {
  readonly name = "fake";
  readonly model = "fake-deterministic-v0";

  async extract(input: ExtractionInput): Promise<LlmResult<ExtractionResponse_>> {
    const suspicious = [
      ...detectInjection(input.contentUnit.body),
      ...input.chunks.flatMap((c) => detectInjection(c.text)),
    ];
    const cohortKeywords = input.cohorts.map((c) => ({ id: c.id, keywords: c.keywords }));
    const signals: ExtractionResponse_["signals"] = [];
    const stages = new Set<ReturnType<typeof detectJourneyStage>>();

    for (const chunk of input.chunks) {
      const detected = detectSignals(chunk.text);
      const stage = detectJourneyStage(chunk.text);
      stages.add(stage);
      const cohortId = matchCohort(chunk.text, cohortKeywords);
      for (const d of detected.slice(0, 6)) {
        signals.push({
          type: d.type,
          normalizedLabel: normalizeLabel(d.type, d.term),
          rawText: firstSentenceContaining(chunk.text, d.term),
          journeyStage: stage,
          cohortId,
          evidenceChunkId: chunk.id,
        });
      }
    }
    if (stages.size === 0) stages.add("UNKNOWN");

    const primaryCohortId = matchCohort(input.contentUnit.body, cohortKeywords);
    const raw = {
      contentUnitId: input.contentUnit.id,
      language: detectLanguage(input.contentUnit.body),
      primaryCohortId,
      secondaryCohortIds: [],
      journeyStages: [...stages],
      contentRole: inferContentRole(signals.map((s) => s.type)),
      signals,
      proofUsed: signals.filter((s) => s.type === "PROOF").map((s) => s.normalizedLabel).slice(0, 10),
      claims: signals.filter((s) => s.type === "CLAIM").map((s) => s.normalizedLabel).slice(0, 10),
      cta: signals.find((s) => s.type === "CTA")?.normalizedLabel ?? null,
    };
    const allowed = allowedFrom(input);
    const data = validateResponse(ExtractionResponseSchema, raw, allowed);
    return result(data, [serializeInput(input)], suspicious);
  }

  async mapDecisionSupport(input: DecisionSupportInput): Promise<LlmResult<DecisionSupportResponse_>> {
    const suspicious = input.vocSignals.flatMap((v) => detectInjection(v.text));
    const needs: DecisionSupportNeed[] = [];
    for (const cohort of input.cohorts) {
      const supportForCohort = (needText: string): string[] =>
        input.vocSignals
          .filter((v) => (v.cohortId === cohort.id || v.cohortId === null) && overlaps(v.text, needText, cohort.keywords))
          .map((v) => v.chunkId)
          .slice(0, 10);

      for (const obj of cohort.objections) {
        needs.push(mkNeed(cohort.id, "OBJECTION", obj, "EVALUATE", supportForCohort(obj)));
      }
      for (const crit of cohort.decisionCriteria) {
        needs.push(mkNeed(cohort.id, "DECISION_CRITERION", crit, "EVALUATE", supportForCohort(crit)));
      }
      if (cohort.activeProblem) {
        needs.push(mkNeed(cohort.id, "QUESTION", cohort.activeProblem, "EXPLORE", supportForCohort(cohort.activeProblem)));
      }
      if (cohort.currentBelief) {
        needs.push(mkNeed(cohort.id, "CURRENT_BELIEF", cohort.currentBelief, "EVALUATE", supportForCohort(cohort.currentBelief)));
      }
      if (cohort.desiredOutcome) {
        needs.push(
          mkNeed(cohort.id, "DESIRED_DECISION_MOVEMENT", cohort.desiredOutcome, "DECIDE", supportForCohort(cohort.desiredOutcome)),
        );
      }
    }
    const allowed = allowedIdsForDecision(input);
    const data = validateResponse(DecisionSupportResponseSchema, { needs: needs.slice(0, 80) }, allowed);
    return result(data, [serializeInput(input)], suspicious);
  }

  async classifyCoverage(input: CoverageInput): Promise<LlmResult<CoverageResponse_>> {
    const classifications: CoverageClassification[] = input.needs.map((need) => {
      const matches = input.ownedUnits.filter((u) => u.matchedNeedKeys.includes(need.needKey));
      if (matches.length === 0) {
        return mkCov(need.needKey, "NONE", [], "No owned asset addresses this need.", false, false, false);
      }
      const withProof = matches.filter((m) => m.hasProofSignal);
      const outdated = matches.every((m) => m.isOutdated);
      const unsupported = matches.some((m) => m.hasUnsupportedClaim) && withProof.length === 0;
      const oversaturated = matches.length >= 4 && withProof.length === 0;

      let status: CoverageClassification["coverageStatus"];
      if (outdated) status = "OUTDATED";
      else if (unsupported) status = "UNSUPPORTED";
      else if (oversaturated) status = "OVERSATURATED";
      else if (withProof.length > 0 && matches.some((m) => m.connectsToOffer)) status = "STRONG";
      else if (withProof.length > 0) status = "PARTIAL";
      else if (matches.some((m) => m.hasCta || m.connectsToOffer)) status = "WEAK";
      else status = "MENTION_ONLY";

      return mkCov(
        need.needKey,
        status,
        matches.map((m) => m.id).slice(0, 20),
        `${matches.length} owned asset(s) touch this need; ${withProof.length} include proof.`,
        withProof.length > 0,
        matches.some((m) => m.connectsToOffer),
        matches.some((m) => m.hasCta),
      );
    });
    const allowed: AllowedIds = {
      chunkIds: new Set(),
      cohortIds: new Set(),
      contentUnitIds: new Set(input.ownedUnits.map((u) => u.id)),
    };
    const data = validateResponse(CoverageResponseSchema, { classifications }, allowed);
    return result(data, [serializeInput(input)], []);
  }

  async generateCandidates(input: CandidateInput): Promise<LlmResult<CandidateGapResponse_>> {
    const suspicious = input.chunks.flatMap((c) => detectInjection(c.text));
    const chunkById = new Map(input.chunks.map((c) => [c.id, c]));
    const cohortPriority = new Map(input.cohorts.map((c) => [c.id, c.priority]));
    const candidates: CandidateGap[] = [];

    for (const need of input.needs) {
      // A candidate generally requires: coverage is not STRONG, and there is demand evidence.
      const uncovered = need.coverageStatus !== "STRONG" && need.coverageStatus !== "OVERSATURATED";
      const hasDemand = need.demandChunkIds.length > 0;
      if (!uncovered || !hasDemand) continue;

      const evidence = buildEvidence(need.demandChunkIds, chunkById);
      const priority = cohortPriority.get(need.cohortId) ?? 3;
      const coverageDeficit = COVERAGE_DEFICIT[need.coverageStatus] ?? 3;
      const gapType = mapNeedToGapType(need.needType, need.coverageStatus);

      candidates.push({
        cohortId: need.cohortId,
        journeyStage: need.journeyStage,
        gapType,
        title: titleFor(gapType, need.normalizedNeed),
        customerQuestionOrBelief: need.normalizedNeed,
        missingDecisionSupport: missingSupportFor(gapType),
        commercialConsequence: consequenceFor(need.journeyStage),
        recommendedContentRole: roleFor(gapType),
        recommendedAssetType: assetFor(gapType),
        suggestedTouchpoint: touchpointFor(need.journeyStage),
        generationReason: `Need "${need.normalizedNeed}" has coverage=${need.coverageStatus} with ${need.demandChunkIds.length} demand evidence item(s).`,
        evidence,
        rankingComponents: {
          commercialImpact: clamp(priority + (need.journeyStage === "DECIDE" || need.journeyStage === "EVALUATE" ? 1 : 0)),
          journeyBlockage: need.journeyStage === "EVALUATE" || need.journeyStage === "DECIDE" ? 5 : 3,
          cohortPriority: clamp(priority),
          demandStrength: clamp(Math.min(5, need.demandChunkIds.length + 2)),
          coverageDeficit,
          strategicAlignment: evidence.some((e) => e.role === "STRATEGIC_PRIORITY") ? 5 : 3,
          competitiveOpportunity: evidence.some((e) => e.role === "COMPETITOR_CONTEXT") ? 3 : 1,
          actionability: 4,
          productionFeasibility: 4,
          learningValue: 3,
        },
      });
    }
    const allowed = allowedIdsForCandidates(input);
    const data = validateResponse(CandidateGapResponseSchema, { candidates: candidates.slice(0, 60) }, allowed);
    return result(data, [serializeInput(input)], suspicious);
  }

  async critique(input: CritiqueInput): Promise<LlmResult<CritiqueVerdict_>> {
    const c = input.candidate;
    let verdict;
    if (!c.hasVerifiedCustomerDemand) {
      verdict = { action: "DOWNGRADE" as const, reason: "No verified first-party customer demand; treat as hypothesis.", mergeWithTitle: null };
    } else if (c.hasVerifiedOwnedCoverageAlready) {
      verdict = { action: "REJECT" as const, reason: "Owned content already answers this need with proof.", mergeWithTitle: null };
    } else if (c.isDuplicateOfTitle) {
      verdict = { action: "MERGE" as const, reason: "Duplicate of an existing candidate.", mergeWithTitle: c.isDuplicateOfTitle };
    } else if (c.looksLikeNonContentProblem) {
      verdict = { action: "MARK_NON_CONTENT" as const, reason: "Appears to be an offer/operational problem, not a content gap.", mergeWithTitle: null };
    } else {
      verdict = { action: "ACCEPT" as const, reason: "Evidenced, non-duplicate, coverage insufficient, cohort relevant.", mergeWithTitle: null };
    }
    const data = CritiqueVerdictSchema.parse(verdict);
    return result(data, [serializeInput(input)], []);
  }
}

// ---- helpers ----

type ExtractionResponse_ = import("@cgi/shared").ExtractionResponse;
type DecisionSupportResponse_ = import("@cgi/shared").DecisionSupportResponse;
type CoverageResponse_ = import("@cgi/shared").CoverageResponse;
type CandidateGapResponse_ = import("@cgi/shared").CandidateGapResponse;
type CritiqueVerdict_ = import("@cgi/shared").CritiqueVerdict;

const COVERAGE_DEFICIT: Record<string, number> = {
  NONE: 5,
  MENTION_ONLY: 4,
  WEAK: 4,
  PARTIAL: 3,
  OUTDATED: 4,
  UNSUPPORTED: 4,
  STRONG: 0,
  OVERSATURATED: 1,
};

function result<T>(data: T, inputTexts: string[], suspicious: string[]): LlmResult<T> {
  const input = inputTexts.join("");
  return {
    data,
    usage: { inputTokens: estimateTokens(input), outputTokens: estimateTokens(JSON.stringify(data)) },
    suspiciousInstructions: suspicious,
  };
}

function serializeInput(input: unknown): string {
  return JSON.stringify(input);
}

function allowedFrom(input: ExtractionInput): AllowedIds {
  return {
    chunkIds: new Set(input.chunks.map((c) => c.id)),
    cohortIds: new Set(input.cohorts.map((c) => c.id)),
    contentUnitIds: new Set([input.contentUnit.id]),
  };
}
function allowedIdsForDecision(input: DecisionSupportInput): AllowedIds {
  return {
    chunkIds: new Set(input.vocSignals.map((v) => v.chunkId)),
    cohortIds: new Set(input.cohorts.map((c) => c.id)),
    contentUnitIds: new Set(),
  };
}
function allowedIdsForCandidates(input: CandidateInput): AllowedIds {
  return {
    chunkIds: new Set(input.chunks.map((c) => c.id)),
    cohortIds: new Set(input.cohorts.map((c) => c.id)),
    contentUnitIds: new Set(),
  };
}

function buildEvidence(chunkIds: string[], chunkById: Map<string, { id: string; text: string; ownerType: string }>) {
  const roleByOwner: Record<string, CandidateGap["evidence"][number]["role"]> = {
    VOC: "CUSTOMER_DEMAND",
    BUSINESS_BRIEF: "STRATEGIC_PRIORITY",
    COMPETITOR: "COMPETITOR_CONTEXT",
    OWNED: "CURRENT_COVERAGE",
  };
  const seen = new Set<string>();
  const evidence: CandidateGap["evidence"] = [];
  for (const id of chunkIds) {
    const chunk = chunkById.get(id);
    if (!chunk || seen.has(id)) continue;
    seen.add(id);
    evidence.push({
      role: roleByOwner[chunk.ownerType] ?? "CUSTOMER_DEMAND",
      chunkId: id,
      exactQuote: chunk.text.trim().slice(0, 240),
    });
    if (evidence.length >= 4) break;
  }
  return evidence;
}

function mkNeed(
  cohortId: string,
  needType: DecisionSupportNeed["needType"],
  text: string,
  stage: DecisionSupportNeed["journeyStage"],
  supportingChunkIds: string[],
): DecisionSupportNeed {
  return {
    cohortId,
    journeyStage: stage,
    needType,
    normalizedNeed: text.slice(0, 300),
    description: "",
    supportingChunkIds,
  };
}

function mkCov(
  needKey: string,
  coverageStatus: CoverageClassification["coverageStatus"],
  matchedContentUnitIds: string[],
  summary: string,
  hasProof: boolean,
  connectsToOffer: boolean,
  hasNextAction: boolean,
): CoverageClassification {
  return { needKey, coverageStatus, matchedContentUnitIds, summary, hasProof, connectsToOffer, hasNextAction };
}

function overlaps(text: string, needText: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  const needTokens = needText.toLowerCase().split(/\s+/).filter((t) => t.length >= 4);
  if (needTokens.some((t) => lower.includes(t))) return true;
  return keywords.some((k) => k && lower.includes(k.toLowerCase()));
}

function normalizeLabel(type: string, term: string): string {
  const map: Record<string, string> = {
    OBJECTION: "objection",
    PROOF: "proof point",
    DESIRED_OUTCOME: "desired outcome",
    DECISION_CRITERION: "decision criterion",
    PAIN: "pain point",
    CTA: "call to action",
    CLAIM: "claim",
    ALTERNATIVE: "alternative comparison",
    QUESTION: "customer question",
  };
  return `${map[type] ?? type.toLowerCase()}: ${term}`.slice(0, 200);
}

function firstSentenceContaining(text: string, term: string): string {
  const idx = text.toLowerCase().indexOf(term.toLowerCase());
  if (idx < 0) return text.slice(0, 200);
  const start = Math.max(0, text.lastIndexOf(".", idx) + 1);
  const endCandidates = [text.indexOf(".", idx), text.indexOf("؟", idx), text.indexOf("?", idx)].filter((n) => n > 0);
  const end = endCandidates.length ? Math.min(...endCandidates) + 1 : Math.min(text.length, idx + 160);
  return text.slice(start, end).trim().slice(0, 300) || text.slice(0, 200);
}

function inferContentRole(types: string[]): import("@cgi/shared").ContentRole {
  if (types.includes("PROOF")) return "PROOF";
  if (types.includes("CTA")) return "CONVERSION";
  if (types.includes("OBJECTION")) return "BRIDGE";
  if (types.includes("QUESTION")) return "VALUE";
  return "AWARENESS";
}

function mapNeedToGapType(needType: string, coverage: string): CandidateGap["gapType"] {
  if (coverage === "OUTDATED") return "FRESHNESS_GAP";
  if (coverage === "UNSUPPORTED") return "EVIDENCE_GAP";
  if (coverage === "OVERSATURATED") return "SATURATION_GAP";
  switch (needType) {
    case "OBJECTION":
      return "OBJECTION_GAP";
    case "CURRENT_BELIEF":
    case "REQUIRED_BELIEF":
      return "BELIEF_GAP";
    case "REQUIRED_PROOF":
      return "PROOF_GAP";
    case "DECISION_CRITERION":
      return "OFFER_CONNECTION_GAP";
    case "QUESTION":
      return "QUESTION_GAP";
    default:
      return "JOURNEY_STAGE_GAP";
  }
}

function titleFor(gapType: string, need: string): string {
  const prefix: Record<string, string> = {
    OBJECTION_GAP: "Missing evidence addressing",
    BELIEF_GAP: "Belief shift needed for",
    PROOF_GAP: "Missing proof for",
    QUESTION_GAP: "Unanswered question:",
    OFFER_CONNECTION_GAP: "No offer connection for",
    FRESHNESS_GAP: "Outdated coverage of",
    EVIDENCE_GAP: "Unsupported claim around",
    SATURATION_GAP: "Oversaturated angle:",
    JOURNEY_STAGE_GAP: "Journey-stage gap:",
  };
  return `${prefix[gapType] ?? "Gap:"} ${need}`.slice(0, 300);
}

function missingSupportFor(gapType: string): string[] {
  const base: Record<string, string[]> = {
    OBJECTION_GAP: ["Direct rebuttal", "Operational proof", "Before/after comparison"],
    PROOF_GAP: ["Case study", "Quantified result", "Third-party validation"],
    BELIEF_GAP: ["Reframe of current belief", "Evidence for better belief"],
    QUESTION_GAP: ["Clear answer", "Worked example"],
    OFFER_CONNECTION_GAP: ["Link to offer mechanism", "Next action"],
    FRESHNESS_GAP: ["Updated data", "Current examples"],
    EVIDENCE_GAP: ["Substantiating proof", "Source citation"],
  };
  return base[gapType] ?? ["Decision support"];
}

function consequenceFor(stage: string): string {
  const map: Record<string, string> = {
    EVALUATE: "The buyer cannot compare confidently and delays or defaults to a competitor.",
    DECIDE: "The buyer stalls at the decision point and the deal slips.",
    EXPLORE: "The prospect never forms the belief needed to consider the offer.",
    TRIGGER: "The prospect does not connect their trigger to this category.",
  };
  return map[stage] ?? "Reduced conversion at this stage.";
}
function roleFor(gapType: string): import("@cgi/shared").ContentRole {
  if (gapType === "PROOF_GAP" || gapType === "EVIDENCE_GAP") return "PROOF";
  if (gapType === "OFFER_CONNECTION_GAP") return "CONVERSION";
  if (gapType === "OBJECTION_GAP") return "BRIDGE";
  return "VALUE";
}
function assetFor(gapType: string): import("@cgi/shared").AssetType {
  const map: Record<string, import("@cgi/shared").AssetType> = {
    OBJECTION_GAP: "PROCESS_BREAKDOWN",
    PROOF_GAP: "CASE_STUDY",
    EVIDENCE_GAP: "PROOF_ASSET",
    QUESTION_GAP: "FAQ",
    OFFER_CONNECTION_GAP: "LANDING_PAGE",
    BELIEF_GAP: "ARTICLE",
    FRESHNESS_GAP: "ARTICLE",
  };
  return map[gapType] ?? "ARTICLE";
}
function touchpointFor(stage: string): string {
  return stage === "DECIDE" ? "LANDING_PAGE_AND_SALES_FOLLOW_UP" : "ARTICLE_AND_NURTURE";
}
function clamp(n: number): number {
  return Math.max(0, Math.min(5, Math.round(n)));
}
