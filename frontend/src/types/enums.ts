// Canonical domain enums (TypeScript). MUST stay in exact parity with
// docs/schemas/enums.json (single source of truth) and backend/app/core/enums.py.
// frontend/src/types/enums.parity.test.ts enforces this. Do not invent variants.

export const FINDING_STATUS = ["observed_fact", "brand_claim", "inference", "hypothesis", "unknown"] as const;
export type FindingStatus = (typeof FINDING_STATUS)[number];

export const CONFIDENCE_LEVEL = ["high", "medium", "low", "insufficient_evidence"] as const;
export type ConfidenceLevel = (typeof CONFIDENCE_LEVEL)[number];

export const SEVERITY_LEVEL = ["critical", "high", "medium", "low"] as const;
export type SeverityLevel = (typeof SEVERITY_LEVEL)[number];

export const REVIEW_STATUS = ["pending", "approved", "rejected", "needs_changes", "auto_accepted"] as const;
export type ReviewStatus = (typeof REVIEW_STATUS)[number];

export const JOB_STATUS = ["queued", "running", "waiting_for_review", "completed", "completed_with_warnings", "failed", "cancelled"] as const;
export type JobStatus = (typeof JOB_STATUS)[number];

export const ANALYSIS_STATUS = ["draft", "collecting", "classifying", "waiting_for_review", "scoring", "report_ready", "approved", "superseded", "failed"] as const;
export type AnalysisStatus = (typeof ANALYSIS_STATUS)[number];

export const PURCHASE_TYPE = ["first_purchase", "repeat_purchase", "upsell", "cross_sell", "renewal", "referral", "return_visit", "subscription_start", "subscription_upgrade", "other"] as const;
export type PurchaseType = (typeof PURCHASE_TYPE)[number];

export const PRIMARY_BOTTLENECK = ["attention", "desire", "persuasion", "friction", "unknown"] as const;
export type PrimaryBottleneck = (typeof PRIMARY_BOTTLENECK)[number];

export const ENTITY_TYPE = ["brand", "competitor"] as const;
export type EntityType = (typeof ENTITY_TYPE)[number];

export const COMPETITOR_TYPE = ["direct", "indirect", "substitute", "category_reference", "unknown"] as const;
export type CompetitorType = (typeof COMPETITOR_TYPE)[number];

export const JOURNEY_STAGE = ["trigger", "exploration", "evaluation", "decision", "activation", "experience", "repeat", "growth", "umot", "unknown", "not_applicable"] as const;
export type JourneyStage = (typeof JOURNEY_STAGE)[number];

export const CONTENT_LAYER = ["front_end_attention", "back_end_selling", "zmot_availability", "umot_sharing", "unknown", "not_applicable"] as const;
export type ContentLayer = (typeof CONTENT_LAYER)[number];

export const MICRO_DECISION_TYPE = ["relevance", "understanding", "trust", "price_acceptance", "proof_acceptance", "risk_reduction", "comparison", "logistics_clarity", "timing", "next_step_readiness", "usage_confidence", "repeat_readiness", "referral_readiness", "other", "unknown"] as const;
export type MicroDecisionType = (typeof MICRO_DECISION_TYPE)[number];

export const BUYING_GROUP_ROLE = ["user", "influencer", "champion", "technical_evaluator", "financial_buyer", "decision_maker", "blocker", "owner_founder", "purchasing_manager", "sales_manager", "merchandising_manager", "business_partner", "parent_caregiver", "individual_buyer", "unknown", "not_applicable"] as const;
export type BuyingGroupRole = (typeof BUYING_GROUP_ROLE)[number];

export const SOURCE_TYPE = ["file", "url", "manual_text", "csv_import", "system_fixture"] as const;
export type SourceType = (typeof SOURCE_TYPE)[number];

export const SOURCE_CATEGORY = ["brand_owned", "customer_voice", "competitor_public", "performance", "business_internal", "operational", "analyst_input"] as const;
export type SourceCategory = (typeof SOURCE_CATEGORY)[number];

export const CONTENT_FORMAT = ["social_post", "reel", "short_video", "long_video", "advertisement", "landing_page", "product_page", "service_page", "website_page", "article", "email", "whatsapp_message", "sales_deck", "catalogue", "faq", "review", "comment", "testimonial", "push_notification", "in_app_message", "search_result", "call_note", "support_ticket", "other"] as const;
export type ContentFormat = (typeof CONTENT_FORMAT)[number];

export const LANGUAGE_CODE = ["ar", "en", "ar_en_mixed", "other", "unknown"] as const;
export type LanguageCode = (typeof LANGUAGE_CODE)[number];

export const SALES_ELEMENT = ["trigger", "claim", "gain", "logistics", "identity", "authority", "social_proof", "claim_proof", "fear_free", "objection_handler", "comparison", "calculation", "reason", "scarcity", "urgency", "reciprocity", "offer"] as const;
export type SalesElement = (typeof SALES_ELEMENT)[number];

export const CLAIM_TYPE = ["functional", "financial", "emotional", "convenience", "quality", "speed", "authority", "risk_reduction", "price", "exclusivity", "status", "logistics", "other"] as const;
export type ClaimType = (typeof CLAIM_TYPE)[number];

export const CLAIM_PROOF_STATUS = ["proven", "partially_proven", "proof_in_progress", "unsupported", "contradicted", "unverifiable"] as const;
export type ClaimProofStatus = (typeof CLAIM_PROOF_STATUS)[number];

export const PROOF_TYPE = ["internal_data", "third_party_data", "certification", "product_specification", "case_study", "customer_testimonial", "customer_review", "demonstration", "calculation", "guarantee", "policy", "authority_credential", "visible_proxy", "other", "none"] as const;
export type ProofType = (typeof PROOF_TYPE)[number];

export const GAP_STATUS = ["candidate", "probable", "confirmed", "rejected", "insufficient_evidence", "not_applicable", "non_content_blocker"] as const;
export type GapStatus = (typeof GAP_STATUS)[number];

export const ROOT_CAUSE_TYPE = ["knowledge_gap", "extraction_gap", "evidence_gap", "coverage_gap", "distribution_gap", "format_gap", "quality_gap", "measurement_gap", "business_gap", "product_gap", "operational_gap", "sales_gap", "unknown"] as const;
export type RootCauseType = (typeof ROOT_CAUSE_TYPE)[number];

export const GAP_TYPE = ["missing_coverage", "weak_coverage", "buying_decision_misalignment", "bottleneck_gap", "journey_gap", "micro_decision_gap", "voc_gap", "objection_gap", "sales_element_gap", "claim_proof_gap", "trust_gap", "buying_group_gap", "touchpoint_availability_gap", "format_gap", "depth_gap", "competitor_differentiation_gap", "market_white_space", "performance_gap", "measurement_gap", "content_readiness_gap", "competitive_coverage_gap", "competitive_depth_gap", "competitive_proof_gap", "competitive_journey_gap", "competitive_buying_group_gap", "competitive_format_gap", "competitive_availability_gap", "competitive_language_gap", "competitor_leak_opportunity", "market_saturation", "false_opportunity", "non_content_gap"] as const;
export type GapType = (typeof GAP_TYPE)[number];

export const EVIDENCE_ROLE = ["supports", "contradicts", "contextual", "customer_voice", "competitor_reference", "performance_signal", "business_context", "operational_context"] as const;
export type EvidenceRole = (typeof EVIDENCE_ROLE)[number];

export const CLASSIFICATION_ORIGIN = ["deterministic", "ai_proposed", "human_assigned", "imported"] as const;
export type ClassificationOrigin = (typeof CLASSIFICATION_ORIGIN)[number];

export const EXTRACTION_QUALITY = ["complete", "partial", "low_quality", "unreadable", "blocked", "unknown"] as const;
export type ExtractionQuality = (typeof EXTRACTION_QUALITY)[number];

export const BANK_TYPE = ["trigger", "objection", "motivation", "satisfaction", "complaint", "switching_reason", "question"] as const;
export type BankType = (typeof BANK_TYPE)[number];

export const PAID_ORGANIC_STATUS = ["paid", "organic", "mixed", "unknown"] as const;
export type PaidOrganicStatus = (typeof PAID_ORGANIC_STATUS)[number];

export const ANALYSIS_TYPE = ["brand_diagnosis", "competitor_diagnosis", "comparative_gap_analysis", "full_diagnosis"] as const;
export type AnalysisType = (typeof ANALYSIS_TYPE)[number];

export const READINESS_DIMENSION = ["expert_author_availability", "evidence_availability", "story_inventory", "product_knowledge", "voc_availability", "production_capacity_realism", "claim_governance", "measurement_readiness"] as const;
export type ReadinessDimension = (typeof READINESS_DIMENSION)[number];

export const READINESS_GRADE = ["a", "b", "c", "d"] as const;
export type ReadinessGrade = (typeof READINESS_GRADE)[number];

export const BRAND_DIAGNOSIS_DIMENSION = ["readiness", "decision_alignment", "journey_coverage", "voc_alignment", "sales_element", "claim_proof", "performance_evidence", "non_content_blocker"] as const;
export type BrandDiagnosisDimension = (typeof BRAND_DIAGNOSIS_DIMENSION)[number];

export const DECISION_ALIGNMENT_LABEL = ["aligned", "not_aligned_with_current_decision"] as const;
export type DecisionAlignmentLabel = (typeof DECISION_ALIGNMENT_LABEL)[number];

export const PERFORMANCE_SIGNAL_TYPE = ["attention", "desire", "persuasion", "friction_reduction", "direct_commercial_outcome", "visible_public_proxy"] as const;
export type PerformanceSignalType = (typeof PERFORMANCE_SIGNAL_TYPE)[number];

export const COLLECTION_STATUS = ["complete", "partial", "empty"] as const;
export type CollectionStatus = (typeof COLLECTION_STATUS)[number];

export const COLLECTION_ITEM_STATUS = ["collected", "blocked", "failed", "skipped"] as const;
export type CollectionItemStatus = (typeof COLLECTION_ITEM_STATUS)[number];

export const SAMPLE_PRESENCE = ["found", "not_found_in_sample", "unknown"] as const;
export type SamplePresence = (typeof SAMPLE_PRESENCE)[number];

// Registry keyed by the canonical enum name used in enums.json. The parity test iterates this.
export const ENUM_REGISTRY: Record<string, readonly string[]> = {
  finding_status: FINDING_STATUS,
  confidence_level: CONFIDENCE_LEVEL,
  severity_level: SEVERITY_LEVEL,
  review_status: REVIEW_STATUS,
  job_status: JOB_STATUS,
  analysis_status: ANALYSIS_STATUS,
  purchase_type: PURCHASE_TYPE,
  primary_bottleneck: PRIMARY_BOTTLENECK,
  entity_type: ENTITY_TYPE,
  competitor_type: COMPETITOR_TYPE,
  journey_stage: JOURNEY_STAGE,
  content_layer: CONTENT_LAYER,
  micro_decision_type: MICRO_DECISION_TYPE,
  buying_group_role: BUYING_GROUP_ROLE,
  source_type: SOURCE_TYPE,
  source_category: SOURCE_CATEGORY,
  content_format: CONTENT_FORMAT,
  language_code: LANGUAGE_CODE,
  sales_element: SALES_ELEMENT,
  claim_type: CLAIM_TYPE,
  claim_proof_status: CLAIM_PROOF_STATUS,
  proof_type: PROOF_TYPE,
  gap_status: GAP_STATUS,
  root_cause_type: ROOT_CAUSE_TYPE,
  gap_type: GAP_TYPE,
  evidence_role: EVIDENCE_ROLE,
  classification_origin: CLASSIFICATION_ORIGIN,
  extraction_quality: EXTRACTION_QUALITY,
  bank_type: BANK_TYPE,
  paid_organic_status: PAID_ORGANIC_STATUS,
  analysis_type: ANALYSIS_TYPE,
  readiness_dimension: READINESS_DIMENSION,
  readiness_grade: READINESS_GRADE,
  brand_diagnosis_dimension: BRAND_DIAGNOSIS_DIMENSION,
  decision_alignment_label: DECISION_ALIGNMENT_LABEL,
  performance_signal_type: PERFORMANCE_SIGNAL_TYPE,
  collection_status: COLLECTION_STATUS,
  collection_item_status: COLLECTION_ITEM_STATUS,
  sample_presence: SAMPLE_PRESENCE,
};
