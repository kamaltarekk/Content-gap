"""Pydantic models for AI structured outputs. Strict: unknown keys rejected, bounds enforced.
Enum values per dimension are validated in `app/ai/validate.py` against the canonical registry."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ConfidenceLevel, LanguageCode

# Dimension name -> canonical enum group name (docs/schemas/enums.json) used for value validation.
DIMENSION_ENUMS: dict[str, str] = {
    "journey_stage": "journey_stage",
    "content_layer": "content_layer",
    "buying_group_role": "buying_group_role",
    "micro_decision_type": "micro_decision_type",
    "primary_bottleneck": "primary_bottleneck",
    "primary_sales_element": "sales_element",
}


class DimensionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str
    confidence: ConfidenceLevel
    evidence_ids: list[str] = Field(min_length=1)
    reasoning: str | None = Field(default=None, max_length=4000)
    custom_label: str | None = None


class CustomerQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=2000)
    confidence: ConfidenceLevel
    evidence_ids: list[str] = Field(min_length=1)


class ClaimResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_text: str = Field(max_length=2000)
    claim_type: str
    finding_status: str
    proof_status: str
    evidence_ids: list[str] = Field(min_length=1)
    proof_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel


class TargetDecisionAlignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: int = Field(ge=0, le=10)
    confidence: ConfidenceLevel
    evidence_ids: list[str] = Field(min_length=1)
    reasoning: str | None = Field(default=None, max_length=4000)


class ContentPieceClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_name: Literal["ContentPieceClassificationResult"]
    content_piece_id: str
    language: LanguageCode
    classifications: dict[str, DimensionResult]
    customer_question: CustomerQuestion | None = None
    claims: list[ClaimResult] = Field(default_factory=list)
    cta: dict | None = None
    target_decision_alignment: TargetDecisionAlignment | None = None
    needs_review: bool
    review_reasons: list[str] = Field(default_factory=list)
