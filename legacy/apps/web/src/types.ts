// Domain types mirroring the backend REST API contract (base http://localhost:3001).

export type Language = "ar" | "en" | "mixed";

export type OwnerType = "OWNED" | "COMPETITOR" | "VOC" | "BUSINESS_BRIEF";

export type SourceType =
  | "URL"
  | "SITEMAP"
  | "FILE_TXT"
  | "FILE_MD"
  | "FILE_CSV"
  | "FILE_JSON"
  | "CAPTURE";

export type UploadFormat = "csv" | "json" | "txt" | "md";

export type JourneyStage =
  | "TRIGGER"
  | "EXPLORE"
  | "EVALUATE"
  | "DECIDE"
  | "EXPERIENCE"
  | "REPEAT";

export const JOURNEY_STAGES: JourneyStage[] = [
  "TRIGGER",
  "EXPLORE",
  "EVALUATE",
  "DECIDE",
  "EXPERIENCE",
  "REPEAT",
];

export type EvidenceStatus =
  | "STRONG_EVIDENCE"
  | "PARTIAL_EVIDENCE"
  | "HYPOTHESIS";

export type PriorityLabel =
  | "P0_CRITICAL_BLOCKER"
  | "P1_PRODUCE_NOW"
  | "P2_PRODUCE_NEXT"
  | "P3_VALIDATE"
  | "P4_MONITOR";

export interface RefreshSchedule {
  dayOfWeek: number; // 0-6
  hourUtc: number; // 0-23
}

export interface Project {
  id: string;
  name: string;
  primaryDomain: string;
  defaultLanguage: Language;
  refreshSchedule: RefreshSchedule;
  [key: string]: unknown;
}

export interface CreateProjectBody {
  name: string;
  primaryDomain: string;
  defaultLanguage: Language;
  refreshSchedule: RefreshSchedule;
}

export interface BusinessBrief {
  businessModel: string;
  commercialObjective: string;
  currentCommercialPriority: string;
  primaryOffer: string;
  offerMechanism: string;
  desiredCustomerAction: string;
  mainConstraints: string;
  positioning: string;
  approvedClaims: string[];
  prohibitedClaims: string[];
  availableProof: string[];
  knownOperationalLimitations: string[];
  markdownNotes: string;
}

export interface OfferBody {
  name: string;
  mechanism: string;
  desiredAction: string;
  approvedClaims: string[];
  prohibitedClaims: string[];
  proof: string[];
  constraints: string[];
}

export interface CohortBody {
  name: string;
  roleIdentity: string;
  commercialSituation: string;
  trigger: string;
  activeProblem: string;
  currentWorkflow: string;
  currentBelief: string;
  desiredOutcome: string;
  objections: string[];
  decisionCriteria: string[];
  priority: number; // 1-5
  offerFit: string;
  exclusionCriteria: string[];
  exactLanguage: string[];
}

export interface Cohort extends CohortBody {
  id: string;
}

export interface CreateSourceBody {
  ownerType: OwnerType;
  competitorSlot: number | null; // 1-3 | null
  sourceType: SourceType;
  name: string;
  url?: string;
  refreshEnabled: boolean;
}

export interface UploadSourceBody {
  ownerType: OwnerType;
  competitorSlot?: number;
  format: UploadFormat;
  name: string;
  content: string;
}

export interface UploadSourceResult {
  sourceId: string;
  importedRows?: number;
  changed: boolean;
}

export interface Source {
  id: string;
  name: string;
  ownerType: OwnerType;
  status: string;
  canonicalUrl: string | null;
  lastSuccessAt: string | null;
  lastFailureAt: string | null;
  errorMessage: string | null;
}

export interface SourcesResponse {
  pending: Source[];
  processed: Source[];
  failed: Source[];
  needsAttention: Source[];
  all: Source[];
}

export interface Run {
  id: string;
  triggerType: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  pipelineVersion: string | null;
  usageJson: {
    estimatedCostUsd?: number;
    ignoredInjectionAttempts?: number;
    [key: string]: unknown;
  } | null;
  outputCountsJson: {
    publishedGaps?: number;
    [key: string]: unknown;
  } | null;
  stageLogJson: unknown;
  errorSummary: string | null;
}

export interface RankingComponents {
  commercialImpact: number;
  journeyBlockage: number;
  cohortPriority: number;
  demandStrength: number;
  coverageDeficit: number;
  strategicAlignment: number;
  competitiveOpportunity: number;
  actionability: number;
  productionFeasibility: number;
  learningValue: number;
}

export const RANKING_COMPONENT_KEYS: (keyof RankingComponents)[] = [
  "commercialImpact",
  "journeyBlockage",
  "cohortPriority",
  "demandStrength",
  "coverageDeficit",
  "strategicAlignment",
  "competitiveOpportunity",
  "actionability",
  "productionFeasibility",
  "learningValue",
];

export interface Gap {
  id: string;
  gapType: string;
  title: string;
  cohortId: string;
  journeyStage: JourneyStage;
  customerNeed: string;
  currentCoverageSummary: string;
  missingDecisionSupport: string[];
  commercialConsequence: string;
  recommendedContentRole: string;
  recommendedAssetType: string;
  suggestedTouchpoint: string;
  evidenceStatus: EvidenceStatus;
  evidenceStatusRule: string;
  priorityLabel: PriorityLabel;
  priorityScore: number; // int, max 90
  rankingComponentsJson: RankingComponents;
  rankingReason: string;
}

export interface EvidenceItem {
  evidenceRole: string;
  exactQuote: string;
  quoteStartOffset: number;
  quoteEndOffset: number;
  chunkId: string;
  contentUnitId: string;
  sourceId: string;
}

export interface GapDetail extends Gap {
  evidence: EvidenceItem[];
}

export type CoverageStatus = string;

export interface CoverageCell {
  cohortId: string;
  journeyStage: JourneyStage;
  needType: string;
  normalizedNeed: string;
  coverageStatus: CoverageStatus;
  supportingAssetCount: number;
}

export interface CoverageMatrixCell {
  cohortId: string;
  journeyStage: JourneyStage;
  requiredNeeds: number;
  strong: number;
  weakOrPartial: number;
  gaps: number;
  evidenceGaps: number;
  oversaturated: number;
}

export interface CoverageResponse {
  cells: CoverageCell[];
  matrix: CoverageMatrixCell[];
}

export interface EvaluationBody {
  evaluatorName: string;
  validityRating: number; // 1-5
  commercialRelevanceRating: number;
  noveltyRating: number;
  evidenceQualityRating: number;
  actionabilityRating: number;
  acceptedIntoPlan: boolean;
  notes: string;
  markedMissedValidGap?: boolean;
}

export interface Evaluation extends EvaluationBody {
  id?: string;
  gapId?: string;
  [key: string]: unknown;
}

export interface RatingAverages {
  validity: number;
  commercialRelevance: number;
  novelty: number;
  evidenceQuality: number;
  actionability: number;
}

export interface ByGroup {
  key: string;
  avgValidity: number;
  count: number;
}

export interface ThresholdChecks {
  validity: boolean;
  relevance: boolean;
  acceptance: boolean;
  evidence: boolean;
  agreement: boolean;
}

export interface Calibration {
  ratingAverages: RatingAverages;
  validity4or5: number;
  relevance4or5: number;
  acceptanceRate: number;
  invalidEvidenceRate: number;
  interRaterKappa: number | null;
  byGapType: ByGroup[];
  byEvidenceStatus: ByGroup[];
  byCohortStage: ByGroup[];
  thresholds: Record<string, number>;
  thresholdChecks: ThresholdChecks;
}

export interface EvaluationsResponse {
  evaluations: Evaluation[];
  calibration: Calibration;
}

export interface ShadowCandidate {
  id: string;
  cohortId: string;
  journeyStage: JourneyStage;
  gapType: string;
  title: string;
  rejectionReason: string;
}

export interface CreateTokenBody {
  projectId: string;
  label: string;
}

export interface TokenResult {
  id: string;
  token: string;
}
