import { z } from "zod";
import {
  ASSET_TYPES,
  CONTENT_ROLES,
  COVERAGE_STATUSES,
  EVIDENCE_ROLES,
  GAP_TYPES,
  JOURNEY_STAGES,
  LANGUAGES,
  OWNER_TYPES,
  SIGNAL_TYPES,
  SOURCE_TYPES,
} from "./enums.js";

// Bounded string helpers — every model-facing field has a max length (injection defense).
const short = z.string().trim().max(300);
const medium = z.string().trim().max(2000);
const longText = z.string().trim().max(20000);
const uuid = z.string().uuid();

// ---------------------------------------------------------------------------
// Setup payloads (external, from dashboard/extension)
// ---------------------------------------------------------------------------
export const ProjectCreateSchema = z.object({
  name: short.min(1),
  primaryDomain: short.min(1),
  defaultLanguage: z.enum(LANGUAGES).default("en"),
  refreshSchedule: z
    .object({ dayOfWeek: z.number().int().min(0).max(6), hourUtc: z.number().int().min(0).max(23) })
    .default({ dayOfWeek: 1, hourUtc: 6 }),
});
export type ProjectCreate = z.infer<typeof ProjectCreateSchema>;

export const BusinessBriefSchema = z.object({
  businessModel: medium.default(""),
  commercialObjective: medium.default(""),
  currentCommercialPriority: medium.default(""),
  primaryOffer: medium.default(""),
  offerMechanism: medium.default(""),
  desiredCustomerAction: medium.default(""),
  mainConstraints: medium.default(""),
  positioning: medium.default(""),
  approvedClaims: z.array(short).max(50).default([]),
  prohibitedClaims: z.array(short).max(50).default([]),
  availableProof: z.array(short).max(50).default([]),
  knownOperationalLimitations: z.array(short).max(50).default([]),
  markdownNotes: longText.default(""),
});
export type BusinessBrief = z.infer<typeof BusinessBriefSchema>;

export const OfferSchema = z.object({
  name: short.min(1),
  mechanism: medium.default(""),
  desiredAction: medium.default(""),
  approvedClaims: z.array(short).max(50).default([]),
  prohibitedClaims: z.array(short).max(50).default([]),
  proof: z.array(short).max(50).default([]),
  constraints: z.array(short).max(50).default([]),
});
export type Offer = z.infer<typeof OfferSchema>;

export const CohortSchema = z.object({
  name: short.min(1),
  roleIdentity: medium.default(""),
  commercialSituation: medium.default(""),
  trigger: medium.default(""),
  activeProblem: medium.default(""),
  currentWorkflow: medium.default(""),
  currentBelief: medium.default(""),
  desiredOutcome: medium.default(""),
  objections: z.array(short).max(50).default([]),
  decisionCriteria: z.array(short).max(50).default([]),
  priority: z.number().int().min(1).max(5).default(3),
  offerFit: medium.default(""),
  exclusionCriteria: z.array(short).max(50).default([]),
  exactLanguage: z.array(short).max(100).default([]),
});
export type Cohort = z.infer<typeof CohortSchema>;

export const SourceCreateSchema = z.object({
  ownerType: z.enum(OWNER_TYPES),
  competitorSlot: z.number().int().min(1).max(3).nullable().default(null),
  sourceType: z.enum(SOURCE_TYPES),
  name: short.min(1),
  url: z.string().url().max(2000).optional(),
  refreshEnabled: z.boolean().default(true),
});
export type SourceCreate = z.infer<typeof SourceCreateSchema>;

export const CaptureSchema = z.object({
  ownerType: z.enum(["OWNED", "COMPETITOR", "VOC"]),
  competitorSlot: z.number().int().min(1).max(3).nullable().default(null),
  url: z.string().url().max(2000),
  title: short.default(""),
  text: longText,
});
export type Capture = z.infer<typeof CaptureSchema>;

export const VocRowSchema = z.object({
  text: medium.min(1),
  sourceType: short.optional(),
  date: short.optional(),
  customerType: short.optional(),
  journeyStage: z.enum(JOURNEY_STAGES).optional(),
  outcome: short.optional(),
  tags: z.array(short).max(30).optional(),
});
export type VocRow = z.infer<typeof VocRowSchema>;

export const EvaluationSchema = z.object({
  evaluatorName: short.min(1),
  validityRating: z.number().int().min(1).max(5),
  commercialRelevanceRating: z.number().int().min(1).max(5),
  noveltyRating: z.number().int().min(1).max(5),
  evidenceQualityRating: z.number().int().min(1).max(5),
  actionabilityRating: z.number().int().min(1).max(5),
  acceptedIntoPlan: z.boolean(),
  notes: medium.default(""),
  // Shadow evaluations may flag a rejected candidate as a missed valid gap.
  markedMissedValidGap: z.boolean().default(false),
});
export type Evaluation = z.infer<typeof EvaluationSchema>;

export const TokenCreateSchema = z.object({
  projectId: uuid,
  label: short.min(1),
  expiresAt: z.string().datetime().nullable().default(null),
});

// ---------------------------------------------------------------------------
// LLM-GENERATED payloads (strictly validated). `.strict()` rejects unknown keys.
// The only IDs the model may use are those provided in its input — enforced by
// validateIdReferences() below, in addition to these schemas.
// ---------------------------------------------------------------------------

export const ExtractedSignalSchema = z
  .object({
    type: z.enum(SIGNAL_TYPES),
    normalizedLabel: short.min(1),
    rawText: medium.min(1),
    journeyStage: z.enum(JOURNEY_STAGES),
    cohortId: uuid.nullable(),
    evidenceChunkId: uuid,
  })
  .strict();

export const ExtractionResponseSchema = z
  .object({
    contentUnitId: uuid,
    language: z.enum(LANGUAGES),
    primaryCohortId: uuid.nullable(),
    secondaryCohortIds: z.array(uuid).max(5).default([]),
    journeyStages: z.array(z.enum(JOURNEY_STAGES)).min(1).max(7),
    contentRole: z.enum(CONTENT_ROLES),
    signals: z.array(ExtractedSignalSchema).max(60),
    proofUsed: z.array(short).max(30).default([]),
    claims: z.array(short).max(30).default([]),
    cta: short.nullable().default(null),
  })
  .strict();
export type ExtractionResponse = z.infer<typeof ExtractionResponseSchema>;

export const DecisionSupportNeedSchema = z
  .object({
    cohortId: uuid,
    journeyStage: z.enum(JOURNEY_STAGES),
    needType: z.enum([
      "QUESTION",
      "OBJECTION",
      "CURRENT_BELIEF",
      "REQUIRED_BELIEF",
      "DECISION_CRITERION",
      "REQUIRED_PROOF",
      "RISK",
      "ALTERNATIVE",
      "DESIRED_DECISION_MOVEMENT",
    ]),
    normalizedNeed: short.min(1),
    description: medium.default(""),
    supportingChunkIds: z.array(uuid).max(20).default([]),
  })
  .strict();
export type DecisionSupportNeed = z.infer<typeof DecisionSupportNeedSchema>;

export const DecisionSupportResponseSchema = z
  .object({ needs: z.array(DecisionSupportNeedSchema).max(80) })
  .strict();
export type DecisionSupportResponse = z.infer<typeof DecisionSupportResponseSchema>;

export const CoverageClassificationSchema = z
  .object({
    needKey: short.min(1),
    coverageStatus: z.enum(COVERAGE_STATUSES),
    matchedContentUnitIds: z.array(uuid).max(20).default([]),
    summary: medium.default(""),
    hasProof: z.boolean().default(false),
    connectsToOffer: z.boolean().default(false),
    hasNextAction: z.boolean().default(false),
  })
  .strict();
export type CoverageClassification = z.infer<typeof CoverageClassificationSchema>;

export const CoverageResponseSchema = z
  .object({ classifications: z.array(CoverageClassificationSchema).max(120) })
  .strict();
export type CoverageResponse = z.infer<typeof CoverageResponseSchema>;

export const CandidateGapSchema = z
  .object({
    cohortId: uuid,
    journeyStage: z.enum(JOURNEY_STAGES),
    gapType: z.enum(GAP_TYPES),
    title: short.min(1),
    customerQuestionOrBelief: medium.default(""),
    missingDecisionSupport: z.array(short).max(20).default([]),
    commercialConsequence: medium.default(""),
    recommendedContentRole: z.enum(CONTENT_ROLES),
    recommendedAssetType: z.enum(ASSET_TYPES),
    suggestedTouchpoint: short.default(""),
    generationReason: medium.default(""),
    // Evidence the model asserts — every id must exist; every quote is re-verified deterministically.
    evidence: z
      .array(
        z
          .object({
            role: z.enum(EVIDENCE_ROLES),
            chunkId: uuid,
            exactQuote: medium.min(1),
          })
          .strict(),
      )
      .max(12)
      .default([]),
    rankingComponents: z
      .object({
        commercialImpact: z.number().int().min(0).max(5),
        journeyBlockage: z.number().int().min(0).max(5),
        cohortPriority: z.number().int().min(0).max(5),
        demandStrength: z.number().int().min(0).max(5),
        coverageDeficit: z.number().int().min(0).max(5),
        strategicAlignment: z.number().int().min(0).max(5),
        competitiveOpportunity: z.number().int().min(0).max(5),
        actionability: z.number().int().min(0).max(5),
        productionFeasibility: z.number().int().min(0).max(5),
        learningValue: z.number().int().min(0).max(5),
      })
      .strict(),
  })
  .strict();
export type CandidateGap = z.infer<typeof CandidateGapSchema>;

export const CandidateGapResponseSchema = z
  .object({ candidates: z.array(CandidateGapSchema).max(60) })
  .strict();
export type CandidateGapResponse = z.infer<typeof CandidateGapResponseSchema>;

export const CritiqueVerdictSchema = z
  .object({
    action: z.enum(["ACCEPT", "DOWNGRADE", "MERGE", "REJECT", "MARK_NON_CONTENT"]),
    reason: medium.min(1),
    mergeWithTitle: short.nullable().default(null),
  })
  .strict();
export type CritiqueVerdict = z.infer<typeof CritiqueVerdictSchema>;

// ---------------------------------------------------------------------------
// ID-reference guard: reject any model output referencing IDs not in the input set.
// This is a hard, non-negotiable defense layered on top of Zod.
// ---------------------------------------------------------------------------
export interface AllowedIds {
  chunkIds: Set<string>;
  cohortIds: Set<string>;
  contentUnitIds: Set<string>;
}

export function collectReferencedIds(value: unknown, keys: string[]): string[] {
  const found: string[] = [];
  const isIdKey = (k: string) => keys.includes(k);
  const walk = (v: unknown, key?: string): void => {
    if (v == null) return;
    if (typeof v === "string") {
      if (key && isIdKey(key)) found.push(v);
      return;
    }
    if (Array.isArray(v)) {
      for (const item of v) walk(item, key);
      return;
    }
    if (typeof v === "object") {
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) walk(val, k);
    }
  };
  walk(value);
  return found;
}

/** Throws UnknownIdError if any referenced id is outside the allowed sets. */
export function validateIdReferences(value: unknown, allowed: AllowedIds): void {
  const chunkRefs = collectReferencedIds(value, ["evidenceChunkId", "chunkId", "supportingChunkIds"]);
  for (const id of chunkRefs) {
    if (!allowed.chunkIds.has(id)) throw new UnknownIdError("chunk", id);
  }
  const cohortRefs = collectReferencedIds(value, ["cohortId", "primaryCohortId", "secondaryCohortIds"]);
  for (const id of cohortRefs) {
    if (id && !allowed.cohortIds.has(id)) throw new UnknownIdError("cohort", id);
  }
  const cuRefs = collectReferencedIds(value, ["contentUnitId", "matchedContentUnitIds"]);
  for (const id of cuRefs) {
    if (!allowed.contentUnitIds.has(id)) throw new UnknownIdError("contentUnit", id);
  }
}

export class UnknownIdError extends Error {
  constructor(
    public readonly kind: string,
    public readonly id: string,
  ) {
    super(`Model referenced unknown ${kind} id: ${id}`);
    this.name = "UnknownIdError";
  }
}
