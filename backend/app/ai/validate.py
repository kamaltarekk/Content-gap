"""Validate AI structured output (spec §6.9, §6.10, §13.3, §20.8). Strict Pydantic parse, closed
enums per dimension, and the hard unknown-evidence-id guard: the model may only cite evidence ids
present in the input manifest. One controlled repair attempt; if it still fails, the item is
routed to needs_review and never persisted as an approved result."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.ai.provider import AIProvider, AIRequest, AIResponse
from app.ai.schemas import DIMENSION_ENUMS, ContentPieceClassificationResult
from app.core.enums import ENUM_REGISTRY


class InvalidStructuredOutput(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class UnknownEvidenceIdError(InvalidStructuredOutput):
    pass


def _collect_evidence_ids(result: ContentPieceClassificationResult) -> list[str]:
    ids: list[str] = []
    for dim in result.classifications.values():
        ids += dim.evidence_ids
    if result.customer_question:
        ids += result.customer_question.evidence_ids
    for claim in result.claims:
        ids += claim.evidence_ids + claim.proof_evidence_ids
    if result.target_decision_alignment:
        ids += result.target_decision_alignment.evidence_ids
    return ids


def validate_classification(raw: dict[str, Any], allowed_evidence_ids: set[str]) -> ContentPieceClassificationResult:
    try:
        result = ContentPieceClassificationResult.model_validate(raw)
    except ValidationError as exc:
        raise InvalidStructuredOutput([f"{e['loc']}: {e['msg']}" for e in exc.errors()]) from exc

    # Closed enums per dimension (the model may not invent a value).
    enum_errors: list[str] = []
    for dim_name, dim in result.classifications.items():
        group = DIMENSION_ENUMS.get(dim_name)
        if group is None:
            enum_errors.append(f"unknown_dimension:{dim_name}")
            continue
        if dim.value not in set(ENUM_REGISTRY[group].values()):
            enum_errors.append(f"invalid_enum:{dim_name}={dim.value}")
    if enum_errors:
        raise InvalidStructuredOutput(enum_errors)

    # Hard unknown-evidence-id guard.
    stray = [eid for eid in _collect_evidence_ids(result) if eid not in allowed_evidence_ids]
    if stray:
        raise UnknownEvidenceIdError([f"unknown_evidence_id:{eid}" for eid in stray])

    return result


async def generate_validated(
    provider: AIProvider,
    request: AIRequest,
    allowed_evidence_ids: set[str],
    idempotency_key: str,
) -> tuple[ContentPieceClassificationResult, AIResponse]:
    """Generate + validate with ONE controlled repair attempt (spec §13.3)."""
    response = await provider.structured_generate(request, idempotency_key)
    try:
        return validate_classification(response.raw, allowed_evidence_ids), response
    except InvalidStructuredOutput as first:
        repair_request = AIRequest(
            task=request.task,
            payload={**request.payload, "repair_hint": first.errors},
            system=request.system,
            prompt_version=request.prompt_version,
        )
        response2 = await provider.structured_generate(repair_request, idempotency_key + ":repair")
        # Raises if the repair still fails — caller marks needs_review, never persists as approved.
        return validate_classification(response2.raw, allowed_evidence_ids), response2
