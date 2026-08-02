import {
  boolean,
  date,
  integer,
  jsonb,
  numeric,
  pgTable,
  text,
  timestamp,
  uuid,
  vector,
} from "drizzle-orm/pg-core";

// Drizzle schema mirrors migrations/0000_init.sql. Snake_case in DB, camelCase in TS.

export const projects = pgTable("projects", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: text("name").notNull(),
  primaryDomain: text("primary_domain").notNull(),
  defaultLanguage: text("default_language").notNull().default("en"),
  status: text("status").notNull().default("ACTIVE"),
  refreshSchedule: jsonb("refresh_schedule").notNull().default({ dayOfWeek: 1, hourUtc: 6 }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const projectTokens = pgTable("project_tokens", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  tokenHash: text("token_hash").notNull().unique(),
  label: text("label").notNull(),
  lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const businessBriefs = pgTable("business_briefs", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  version: integer("version").notNull().default(1),
  structuredDataJson: jsonb("structured_data_json").notNull(),
  markdownNotes: text("markdown_notes").notNull().default(""),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const offers = pgTable("offers", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  name: text("name").notNull(),
  mechanism: text("mechanism").notNull().default(""),
  desiredAction: text("desired_action").notNull().default(""),
  approvedClaimsJson: jsonb("approved_claims_json").notNull().default([]),
  prohibitedClaimsJson: jsonb("prohibited_claims_json").notNull().default([]),
  proofJson: jsonb("proof_json").notNull().default([]),
  constraintsJson: jsonb("constraints_json").notNull().default([]),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const cohorts = pgTable("cohorts", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  name: text("name").notNull(),
  roleIdentity: text("role_identity").notNull().default(""),
  commercialSituation: text("commercial_situation").notNull().default(""),
  trigger: text("trigger").notNull().default(""),
  activeProblem: text("active_problem").notNull().default(""),
  currentWorkflow: text("current_workflow").notNull().default(""),
  currentBelief: text("current_belief").notNull().default(""),
  desiredOutcome: text("desired_outcome").notNull().default(""),
  objectionsJson: jsonb("objections_json").notNull().default([]),
  decisionCriteriaJson: jsonb("decision_criteria_json").notNull().default([]),
  priority: integer("priority").notNull().default(3),
  offerFit: text("offer_fit").notNull().default(""),
  exclusionCriteriaJson: jsonb("exclusion_criteria_json").notNull().default([]),
  exactLanguageJson: jsonb("exact_language_json").notNull().default([]),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const sources = pgTable("sources", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  ownerType: text("owner_type").notNull(),
  competitorSlot: integer("competitor_slot"),
  sourceType: text("source_type").notNull(),
  name: text("name").notNull(),
  canonicalUrl: text("canonical_url"),
  crawlMethod: text("crawl_method").notNull().default("HTTP"),
  refreshEnabled: boolean("refresh_enabled").notNull().default(true),
  refreshInterval: text("refresh_interval").notNull().default("WEEKLY"),
  lastSuccessAt: timestamp("last_success_at", { withTimezone: true }),
  lastFailureAt: timestamp("last_failure_at", { withTimezone: true }),
  status: text("status").notNull().default("PENDING"),
  errorMessage: text("error_message"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const sourceSnapshots = pgTable("source_snapshots", {
  id: uuid("id").primaryKey().defaultRandom(),
  sourceId: uuid("source_id").notNull(),
  contentHash: text("content_hash").notNull(),
  rawContent: text("raw_content").notNull(),
  normalizedContent: text("normalized_content").notNull(),
  metadataJson: jsonb("metadata_json").notNull().default({}),
  capturedAt: timestamp("captured_at", { withTimezone: true }).notNull().defaultNow(),
  isCurrent: boolean("is_current").notNull().default(true),
});

export const contentUnits = pgTable("content_units", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  sourceSnapshotId: uuid("source_snapshot_id").notNull(),
  title: text("title").notNull().default(""),
  body: text("body").notNull(),
  language: text("language").notNull().default("unknown"),
  publishedAt: date("published_at"),
  assetType: text("asset_type").notNull().default("UNKNOWN"),
  platform: text("platform"),
  url: text("url"),
  metadataJson: jsonb("metadata_json").notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const chunks = pgTable("chunks", {
  id: uuid("id").primaryKey().defaultRandom(),
  contentUnitId: uuid("content_unit_id").notNull(),
  chunkIndex: integer("chunk_index").notNull(),
  text: text("text").notNull(),
  startOffset: integer("start_offset").notNull(),
  endOffset: integer("end_offset").notNull(),
  embedding: vector("embedding", { dimensions: 384 }),
  tokenCount: integer("token_count").notNull().default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const extractedSignals = pgTable("extracted_signals", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  contentUnitId: uuid("content_unit_id").notNull(),
  chunkId: uuid("chunk_id"),
  signalType: text("signal_type").notNull(),
  normalizedLabel: text("normalized_label").notNull(),
  rawText: text("raw_text").notNull(),
  structuredDataJson: jsonb("structured_data_json").notNull().default({}),
  cohortId: uuid("cohort_id"),
  journeyStage: text("journey_stage").notNull().default("UNKNOWN"),
  evidenceWeight: integer("evidence_weight").notNull().default(1),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const decisionNeeds = pgTable("decision_needs", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  cohortId: uuid("cohort_id").notNull(),
  journeyStage: text("journey_stage").notNull(),
  needType: text("need_type").notNull(),
  normalizedNeed: text("normalized_need").notNull(),
  description: text("description").notNull().default(""),
  evidenceJson: jsonb("evidence_json").notNull().default([]),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const coverageCells = pgTable("coverage_cells", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  cohortId: uuid("cohort_id").notNull(),
  journeyStage: text("journey_stage").notNull(),
  needType: text("need_type").notNull(),
  normalizedNeed: text("normalized_need").notNull(),
  coverageStatus: text("coverage_status").notNull(),
  coverageStrength: integer("coverage_strength").notNull().default(0),
  supportingAssetCount: integer("supporting_asset_count").notNull().default(0),
  effectiveAssetCount: integer("effective_asset_count").notNull().default(0),
  evidenceJson: jsonb("evidence_json").notNull().default([]),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const gapCandidates = pgTable("gap_candidates", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  runId: uuid("run_id"),
  cohortId: uuid("cohort_id"),
  journeyStage: text("journey_stage").notNull(),
  gapType: text("gap_type").notNull(),
  title: text("title").notNull(),
  candidateDataJson: jsonb("candidate_data_json").notNull(),
  generationReason: text("generation_reason").notNull().default(""),
  status: text("status").notNull().default("CANDIDATE"),
  rejectionReason: text("rejection_reason"),
  priorityScore: integer("priority_score").notNull().default(0),
  priorityLabel: text("priority_label").notNull().default("P5_REJECT"),
  isShadowSample: boolean("is_shadow_sample").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const gaps = pgTable("gaps", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  gapCandidateId: uuid("gap_candidate_id"),
  runId: uuid("run_id"),
  cohortId: uuid("cohort_id"),
  journeyStage: text("journey_stage").notNull(),
  gapType: text("gap_type").notNull(),
  title: text("title").notNull(),
  customerNeed: text("customer_need").notNull().default(""),
  currentCoverageSummary: text("current_coverage_summary").notNull().default(""),
  missingDecisionSupport: jsonb("missing_decision_support").notNull().default([]),
  commercialConsequence: text("commercial_consequence").notNull().default(""),
  recommendedContentRole: text("recommended_content_role").notNull().default("VALUE"),
  recommendedAssetType: text("recommended_asset_type").notNull().default("ARTICLE"),
  suggestedTouchpoint: text("suggested_touchpoint").notNull().default(""),
  evidenceStatus: text("evidence_status").notNull().default("HYPOTHESIS"),
  evidenceStatusRule: text("evidence_status_rule").notNull().default(""),
  priorityLabel: text("priority_label").notNull().default("P4_MONITOR"),
  priorityScore: integer("priority_score").notNull().default(0),
  rankingComponentsJson: jsonb("ranking_components_json").notNull().default({}),
  rankingReason: text("ranking_reason").notNull().default(""),
  status: text("status").notNull().default("PUBLISHED"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const gapEvidence = pgTable("gap_evidence", {
  id: uuid("id").primaryKey().defaultRandom(),
  gapId: uuid("gap_id").notNull(),
  sourceId: uuid("source_id"),
  sourceSnapshotId: uuid("source_snapshot_id"),
  contentUnitId: uuid("content_unit_id"),
  chunkId: uuid("chunk_id"),
  evidenceRole: text("evidence_role").notNull(),
  exactQuote: text("exact_quote").notNull(),
  quoteStartOffset: integer("quote_start_offset").notNull(),
  quoteEndOffset: integer("quote_end_offset").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const evaluations = pgTable("evaluations", {
  id: uuid("id").primaryKey().defaultRandom(),
  gapId: uuid("gap_id"),
  gapCandidateId: uuid("gap_candidate_id"),
  evaluatorName: text("evaluator_name").notNull(),
  validityRating: integer("validity_rating").notNull(),
  commercialRelevanceRating: integer("commercial_relevance_rating").notNull(),
  noveltyRating: integer("novelty_rating").notNull(),
  evidenceQualityRating: integer("evidence_quality_rating").notNull(),
  actionabilityRating: integer("actionability_rating").notNull(),
  acceptedIntoPlan: boolean("accepted_into_plan").notNull().default(false),
  markedMissedValidGap: boolean("marked_missed_valid_gap").notNull().default(false),
  notes: text("notes").notNull().default(""),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const outcomes = pgTable("outcomes", {
  id: uuid("id").primaryKey().defaultRandom(),
  gapId: uuid("gap_id").notNull(),
  addressed: boolean("addressed").notNull().default(false),
  contentAssetUrl: text("content_asset_url"),
  publicationDate: date("publication_date"),
  enteredContentPlan: boolean("entered_content_plan").notNull().default(false),
  qualifiedConversationsBefore: integer("qualified_conversations_before"),
  qualifiedConversationsAfter: integer("qualified_conversations_after"),
  conversionObservations: text("conversion_observations"),
  objectionFrequencyBefore: integer("objection_frequency_before"),
  objectionFrequencyAfter: integer("objection_frequency_after"),
  qualitativeOutcome: text("qualitative_outcome"),
  outcomeNotes: text("outcome_notes"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const analysisRuns = pgTable("analysis_runs", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  triggerType: text("trigger_type").notNull(),
  status: text("status").notNull().default("QUEUED"),
  pipelineVersion: text("pipeline_version").notNull(),
  startedAt: timestamp("started_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  errorSummary: text("error_summary"),
  stageLogJson: jsonb("stage_log_json").notNull().default([]),
  inputCountsJson: jsonb("input_counts_json").notNull().default({}),
  outputCountsJson: jsonb("output_counts_json").notNull().default({}),
  usageJson: jsonb("usage_json").notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const usageEvents = pgTable("usage_events", {
  id: uuid("id").primaryKey().defaultRandom(),
  projectId: uuid("project_id").notNull(),
  runId: uuid("run_id"),
  provider: text("provider").notNull(),
  model: text("model").notNull(),
  operation: text("operation").notNull(),
  inputTokens: integer("input_tokens").notNull().default(0),
  outputTokens: integer("output_tokens").notNull().default(0),
  estimatedCost: numeric("estimated_cost", { precision: 12, scale: 6 }).notNull().default("0"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});
