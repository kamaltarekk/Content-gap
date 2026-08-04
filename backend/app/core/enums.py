"""Canonical domain enums.

These MUST stay in exact parity with ``docs/schemas/enums.json`` (the single source of
truth shared with the frontend). ``backend/tests/test_enum_parity.py`` enforces this.
Do not invent variants. Strings are exact per Section 7 of the build spec.
"""

from __future__ import annotations

from enum import StrEnum


class BaseStrEnum(StrEnum):
    """String enum whose ``value`` is the canonical wire string."""

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


class FindingStatus(BaseStrEnum):
    observed_fact = "observed_fact"
    brand_claim = "brand_claim"
    inference = "inference"
    hypothesis = "hypothesis"
    unknown = "unknown"


class ConfidenceLevel(BaseStrEnum):
    high = "high"
    medium = "medium"
    low = "low"
    insufficient_evidence = "insufficient_evidence"


class SeverityLevel(BaseStrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ReviewStatus(BaseStrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    needs_changes = "needs_changes"
    auto_accepted = "auto_accepted"


class JobStatus(BaseStrEnum):
    queued = "queued"
    running = "running"
    waiting_for_review = "waiting_for_review"
    completed = "completed"
    completed_with_warnings = "completed_with_warnings"
    failed = "failed"
    cancelled = "cancelled"


class AnalysisStatus(BaseStrEnum):
    draft = "draft"
    collecting = "collecting"
    classifying = "classifying"
    waiting_for_review = "waiting_for_review"
    scoring = "scoring"
    report_ready = "report_ready"
    approved = "approved"
    superseded = "superseded"
    failed = "failed"


class PurchaseType(BaseStrEnum):
    first_purchase = "first_purchase"
    repeat_purchase = "repeat_purchase"
    upsell = "upsell"
    cross_sell = "cross_sell"
    renewal = "renewal"
    referral = "referral"
    return_visit = "return_visit"
    subscription_start = "subscription_start"
    subscription_upgrade = "subscription_upgrade"
    other = "other"


class PrimaryBottleneck(BaseStrEnum):
    attention = "attention"
    desire = "desire"
    persuasion = "persuasion"
    friction = "friction"
    unknown = "unknown"


class EntityType(BaseStrEnum):
    brand = "brand"
    competitor = "competitor"


class CompetitorType(BaseStrEnum):
    direct = "direct"
    indirect = "indirect"
    substitute = "substitute"
    category_reference = "category_reference"
    unknown = "unknown"


class JourneyStage(BaseStrEnum):
    trigger = "trigger"
    exploration = "exploration"
    evaluation = "evaluation"
    decision = "decision"
    activation = "activation"
    experience = "experience"
    repeat = "repeat"
    growth = "growth"
    umot = "umot"
    unknown = "unknown"
    not_applicable = "not_applicable"


class ContentLayer(BaseStrEnum):
    front_end_attention = "front_end_attention"
    back_end_selling = "back_end_selling"
    zmot_availability = "zmot_availability"
    umot_sharing = "umot_sharing"
    unknown = "unknown"
    not_applicable = "not_applicable"


class MicroDecisionType(BaseStrEnum):
    relevance = "relevance"
    understanding = "understanding"
    trust = "trust"
    price_acceptance = "price_acceptance"
    proof_acceptance = "proof_acceptance"
    risk_reduction = "risk_reduction"
    comparison = "comparison"
    logistics_clarity = "logistics_clarity"
    timing = "timing"
    next_step_readiness = "next_step_readiness"
    usage_confidence = "usage_confidence"
    repeat_readiness = "repeat_readiness"
    referral_readiness = "referral_readiness"
    other = "other"
    unknown = "unknown"


class BuyingGroupRole(BaseStrEnum):
    user = "user"
    influencer = "influencer"
    champion = "champion"
    technical_evaluator = "technical_evaluator"
    financial_buyer = "financial_buyer"
    decision_maker = "decision_maker"
    blocker = "blocker"
    owner_founder = "owner_founder"
    purchasing_manager = "purchasing_manager"
    sales_manager = "sales_manager"
    merchandising_manager = "merchandising_manager"
    business_partner = "business_partner"
    parent_caregiver = "parent_caregiver"
    individual_buyer = "individual_buyer"
    unknown = "unknown"
    not_applicable = "not_applicable"


class SourceType(BaseStrEnum):
    file = "file"
    url = "url"
    manual_text = "manual_text"
    csv_import = "csv_import"
    system_fixture = "system_fixture"


class SourceCategory(BaseStrEnum):
    brand_owned = "brand_owned"
    customer_voice = "customer_voice"
    competitor_public = "competitor_public"
    performance = "performance"
    business_internal = "business_internal"
    operational = "operational"
    analyst_input = "analyst_input"


class ContentFormat(BaseStrEnum):
    social_post = "social_post"
    reel = "reel"
    short_video = "short_video"
    long_video = "long_video"
    advertisement = "advertisement"
    landing_page = "landing_page"
    product_page = "product_page"
    service_page = "service_page"
    website_page = "website_page"
    article = "article"
    email = "email"
    whatsapp_message = "whatsapp_message"
    sales_deck = "sales_deck"
    catalogue = "catalogue"
    faq = "faq"
    review = "review"
    comment = "comment"
    testimonial = "testimonial"
    push_notification = "push_notification"
    in_app_message = "in_app_message"
    search_result = "search_result"
    call_note = "call_note"
    support_ticket = "support_ticket"
    other = "other"


class LanguageCode(BaseStrEnum):
    ar = "ar"
    en = "en"
    ar_en_mixed = "ar_en_mixed"
    other = "other"
    unknown = "unknown"


class SalesElement(BaseStrEnum):
    trigger = "trigger"
    claim = "claim"
    gain = "gain"
    logistics = "logistics"
    identity = "identity"
    authority = "authority"
    social_proof = "social_proof"
    claim_proof = "claim_proof"
    fear_free = "fear_free"
    objection_handler = "objection_handler"
    comparison = "comparison"
    calculation = "calculation"
    reason = "reason"
    scarcity = "scarcity"
    urgency = "urgency"
    reciprocity = "reciprocity"
    offer = "offer"


class ClaimType(BaseStrEnum):
    functional = "functional"
    financial = "financial"
    emotional = "emotional"
    convenience = "convenience"
    quality = "quality"
    speed = "speed"
    authority = "authority"
    risk_reduction = "risk_reduction"
    price = "price"
    exclusivity = "exclusivity"
    status = "status"
    logistics = "logistics"
    other = "other"


class ClaimProofStatus(BaseStrEnum):
    proven = "proven"
    partially_proven = "partially_proven"
    proof_in_progress = "proof_in_progress"
    unsupported = "unsupported"
    contradicted = "contradicted"
    unverifiable = "unverifiable"


class ProofType(BaseStrEnum):
    internal_data = "internal_data"
    third_party_data = "third_party_data"
    certification = "certification"
    product_specification = "product_specification"
    case_study = "case_study"
    customer_testimonial = "customer_testimonial"
    customer_review = "customer_review"
    demonstration = "demonstration"
    calculation = "calculation"
    guarantee = "guarantee"
    policy = "policy"
    authority_credential = "authority_credential"
    visible_proxy = "visible_proxy"
    other = "other"
    none = "none"


class GapStatus(BaseStrEnum):
    candidate = "candidate"
    probable = "probable"
    confirmed = "confirmed"
    rejected = "rejected"
    insufficient_evidence = "insufficient_evidence"
    not_applicable = "not_applicable"
    non_content_blocker = "non_content_blocker"


class RootCauseType(BaseStrEnum):
    knowledge_gap = "knowledge_gap"
    extraction_gap = "extraction_gap"
    evidence_gap = "evidence_gap"
    coverage_gap = "coverage_gap"
    distribution_gap = "distribution_gap"
    format_gap = "format_gap"
    quality_gap = "quality_gap"
    measurement_gap = "measurement_gap"
    business_gap = "business_gap"
    product_gap = "product_gap"
    operational_gap = "operational_gap"
    sales_gap = "sales_gap"
    unknown = "unknown"


class GapType(BaseStrEnum):
    missing_coverage = "missing_coverage"
    weak_coverage = "weak_coverage"
    buying_decision_misalignment = "buying_decision_misalignment"
    bottleneck_gap = "bottleneck_gap"
    journey_gap = "journey_gap"
    micro_decision_gap = "micro_decision_gap"
    voc_gap = "voc_gap"
    objection_gap = "objection_gap"
    sales_element_gap = "sales_element_gap"
    claim_proof_gap = "claim_proof_gap"
    trust_gap = "trust_gap"
    buying_group_gap = "buying_group_gap"
    touchpoint_availability_gap = "touchpoint_availability_gap"
    format_gap = "format_gap"
    depth_gap = "depth_gap"
    competitor_differentiation_gap = "competitor_differentiation_gap"
    market_white_space = "market_white_space"
    performance_gap = "performance_gap"
    measurement_gap = "measurement_gap"
    content_readiness_gap = "content_readiness_gap"
    competitive_coverage_gap = "competitive_coverage_gap"
    competitive_depth_gap = "competitive_depth_gap"
    competitive_proof_gap = "competitive_proof_gap"
    competitive_journey_gap = "competitive_journey_gap"
    competitive_buying_group_gap = "competitive_buying_group_gap"
    competitive_format_gap = "competitive_format_gap"
    competitive_availability_gap = "competitive_availability_gap"
    competitive_language_gap = "competitive_language_gap"
    competitor_leak_opportunity = "competitor_leak_opportunity"
    market_saturation = "market_saturation"
    false_opportunity = "false_opportunity"
    non_content_gap = "non_content_gap"


class EvidenceRole(BaseStrEnum):
    supports = "supports"
    contradicts = "contradicts"
    contextual = "contextual"
    customer_voice = "customer_voice"
    competitor_reference = "competitor_reference"
    performance_signal = "performance_signal"
    business_context = "business_context"
    operational_context = "operational_context"


class ClassificationOrigin(BaseStrEnum):
    deterministic = "deterministic"
    ai_proposed = "ai_proposed"
    human_assigned = "human_assigned"
    imported = "imported"


class ExtractionQuality(BaseStrEnum):
    complete = "complete"
    partial = "partial"
    low_quality = "low_quality"
    unreadable = "unreadable"
    blocked = "blocked"
    unknown = "unknown"


class BankType(BaseStrEnum):
    trigger = "trigger"
    objection = "objection"
    motivation = "motivation"
    satisfaction = "satisfaction"
    complaint = "complaint"
    switching_reason = "switching_reason"
    question = "question"


class PaidOrganicStatus(BaseStrEnum):
    paid = "paid"
    organic = "organic"
    mixed = "mixed"
    unknown = "unknown"


class AnalysisType(BaseStrEnum):
    brand_diagnosis = "brand_diagnosis"
    competitor_diagnosis = "competitor_diagnosis"
    comparative_gap_analysis = "comparative_gap_analysis"
    full_diagnosis = "full_diagnosis"


# Registry keyed by the canonical enum name used in enums.json. The parity test iterates this.
ENUM_REGISTRY: dict[str, type[BaseStrEnum]] = {
    "finding_status": FindingStatus,
    "confidence_level": ConfidenceLevel,
    "severity_level": SeverityLevel,
    "review_status": ReviewStatus,
    "job_status": JobStatus,
    "analysis_status": AnalysisStatus,
    "purchase_type": PurchaseType,
    "primary_bottleneck": PrimaryBottleneck,
    "entity_type": EntityType,
    "competitor_type": CompetitorType,
    "journey_stage": JourneyStage,
    "content_layer": ContentLayer,
    "micro_decision_type": MicroDecisionType,
    "buying_group_role": BuyingGroupRole,
    "source_type": SourceType,
    "source_category": SourceCategory,
    "content_format": ContentFormat,
    "language_code": LanguageCode,
    "sales_element": SalesElement,
    "claim_type": ClaimType,
    "claim_proof_status": ClaimProofStatus,
    "proof_type": ProofType,
    "gap_status": GapStatus,
    "root_cause_type": RootCauseType,
    "gap_type": GapType,
    "evidence_role": EvidenceRole,
    "classification_origin": ClassificationOrigin,
    "extraction_quality": ExtractionQuality,
    "bank_type": BankType,
    "paid_organic_status": PaidOrganicStatus,
    "analysis_type": AnalysisType,
}
