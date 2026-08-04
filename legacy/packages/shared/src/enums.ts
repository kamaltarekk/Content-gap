// Central enum definitions. Each is a readonly tuple + a derived union type so the
// same values back Zod validators (see schemas.ts) and Drizzle columns.

export const OWNER_TYPES = ["BUSINESS_BRIEF", "OWNED", "VOC", "COMPETITOR"] as const;
export type OwnerType = (typeof OWNER_TYPES)[number];

export const SOURCE_TYPES = [
  "URL",
  "SITEMAP",
  "FILE_TXT",
  "FILE_MD",
  "FILE_CSV",
  "FILE_JSON",
  "CAPTURE",
] as const;
export type SourceType = (typeof SOURCE_TYPES)[number];

export const CRAWL_METHODS = ["HTTP", "PLAYWRIGHT", "UPLOAD", "CAPTURE"] as const;
export type CrawlMethod = (typeof CRAWL_METHODS)[number];

export const SOURCE_STATUSES = [
  "PENDING",
  "PROCESSING",
  "PROCESSED",
  "FAILED",
  "NEEDS_ATTENTION",
] as const;
export type SourceStatus = (typeof SOURCE_STATUSES)[number];

export const SIGNAL_TYPES = [
  "QUESTION",
  "OBJECTION",
  "BELIEF",
  "TRIGGER",
  "PAIN",
  "DESIRED_OUTCOME",
  "DECISION_CRITERION",
  "PROOF",
  "CLAIM",
  "ALTERNATIVE",
  "CTA",
  "COMMERCIAL_CONSEQUENCE",
] as const;
export type SignalType = (typeof SIGNAL_TYPES)[number];

export const JOURNEY_STAGES = [
  "TRIGGER",
  "EXPLORE",
  "EVALUATE",
  "DECIDE",
  "EXPERIENCE",
  "REPEAT",
  "UNKNOWN",
] as const;
export type JourneyStage = (typeof JOURNEY_STAGES)[number];

export const CONTENT_ROLES = ["AWARENESS", "VALUE", "BRIDGE", "PROOF", "CONVERSION", "RETENTION"] as const;
export type ContentRole = (typeof CONTENT_ROLES)[number];

export const ASSET_TYPES = [
  "ARTICLE",
  "LANDING_PAGE",
  "CASE_STUDY",
  "PROCESS_BREAKDOWN",
  "COMPARISON",
  "FAQ",
  "GUIDE",
  "PROOF_ASSET",
  "VIDEO_TRANSCRIPT",
  "SOCIAL_POST",
  "UNKNOWN",
] as const;
export type AssetType = (typeof ASSET_TYPES)[number];

export const COVERAGE_STATUSES = [
  "NONE",
  "MENTION_ONLY",
  "WEAK",
  "PARTIAL",
  "STRONG",
  "OUTDATED",
  "UNSUPPORTED",
  "OVERSATURATED",
] as const;
export type CoverageStatus = (typeof COVERAGE_STATUSES)[number];

export const GAP_TYPES = [
  "COHORT_COVERAGE_GAP",
  "JOURNEY_STAGE_GAP",
  "QUESTION_GAP",
  "OBJECTION_GAP",
  "BELIEF_GAP",
  "PROOF_GAP",
  "OFFER_CONNECTION_GAP",
  "TOUCHPOINT_GAP",
  "FORMAT_GAP",
  "COMPETITOR_WHITE_SPACE",
  "FRESHNESS_GAP",
  "DUPLICATION_GAP",
  "SATURATION_GAP",
  "EVIDENCE_GAP",
] as const;
export type GapType = (typeof GAP_TYPES)[number];

export const EVIDENCE_STATUSES = ["STRONG_EVIDENCE", "PARTIAL_EVIDENCE", "HYPOTHESIS"] as const;
export type EvidenceStatus = (typeof EVIDENCE_STATUSES)[number];

export const EVIDENCE_ROLES = [
  "CUSTOMER_DEMAND",
  "STRATEGIC_PRIORITY",
  "CURRENT_COVERAGE",
  "COMPETITOR_CONTEXT",
  "COMMERCIAL_CONSEQUENCE",
  "MISSING_PROOF",
] as const;
export type EvidenceRole = (typeof EVIDENCE_ROLES)[number];

export const PRIORITY_LABELS = [
  "P0_CRITICAL_BLOCKER",
  "P1_PRODUCE_NOW",
  "P2_PRODUCE_NEXT",
  "P3_VALIDATE",
  "P4_MONITOR",
  "P5_REJECT",
] as const;
export type PriorityLabel = (typeof PRIORITY_LABELS)[number];

export const GAP_CANDIDATE_STATUSES = [
  "CANDIDATE",
  "VERIFIED",
  "PUBLISHED",
  "REJECTED",
  "MERGED",
  "SHADOW",
] as const;
export type GapCandidateStatus = (typeof GAP_CANDIDATE_STATUSES)[number];

export const RUN_TRIGGER_TYPES = ["INGESTION", "WEEKLY_REFRESH", "MANUAL_SETUP", "TEST"] as const;
export type RunTriggerType = (typeof RUN_TRIGGER_TYPES)[number];

export const RUN_STATUSES = ["QUEUED", "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED"] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

export const LANGUAGES = ["ar", "en", "mixed", "unknown"] as const;
export type Language = (typeof LANGUAGES)[number];

// Rating scale used across evaluation dimensions (1..5).
export const RATINGS = [1, 2, 3, 4, 5] as const;
export type Rating = (typeof RATINGS)[number];
