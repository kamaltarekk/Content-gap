"""Content classification service. Deterministic code owns fingerprinting, caching, evidence-id
checks, and persistence; the AI only proposes. Invalid output never becomes an approved result."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, AIRequest
from app.ai.validate import InvalidStructuredOutput, generate_validated
from app.core.text import sha256_text
from app.db.models.classification import ContentClassification
from app.db.models.content_piece import ContentPiece, EvidenceSpan

logger = logging.getLogger("cdga.classify")
SCHEMA_VERSION = "1"


@dataclass
class ClassifyOutcome:
    content_piece_id: uuid.UUID
    status: str  # classified | cache_hit | needs_review
    classification_ids: list[uuid.UUID]
    suspicious_instructions: list[str]


def classification_fingerprint(content_hash: str, context_version_id: str, prompt_version: str, model_id: str) -> str:
    return sha256_text(f"{content_hash}|{context_version_id}|{prompt_version}|{model_id}|{SCHEMA_VERSION}")


async def classify_piece(
    session: AsyncSession,
    provider: AIProvider,
    *,
    piece: ContentPiece,
    context_version_id: str,
    prompt_version: str = "v1",
    force: bool = False,
) -> ClassifyOutcome:
    fingerprint = classification_fingerprint(piece.content_hash, context_version_id, prompt_version, provider.model)

    if not force:
        cached = (
            (
                await session.execute(
                    select(ContentClassification).where(
                        ContentClassification.content_piece_id == piece.id,
                        ContentClassification.fingerprint == fingerprint,
                        ContentClassification.is_current.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        if cached:
            return ClassifyOutcome(piece.id, "cache_hit", [c.id for c in cached], [])

    spans = (
        (await session.execute(select(EvidenceSpan).where(EvidenceSpan.content_piece_id == piece.id))).scalars().all()
    )
    evidence_ids = [str(s.id) for s in spans]
    allowed = set(evidence_ids)

    request = AIRequest(
        task="content_piece_classification",
        payload={
            "content_piece_id": str(piece.id),
            "text": piece.original_text,
            "language": piece.language_code,
            "evidence_ids": evidence_ids,
        },
        prompt_version=prompt_version,
    )

    try:
        result, response = await generate_validated(provider, request, allowed, idempotency_key=fingerprint)
    except InvalidStructuredOutput as exc:
        # Invalid output is never persisted as an approved result (spec gate).
        logger.warning("classification rejected for piece=%s: %s", piece.id, exc.errors)
        return ClassifyOutcome(piece.id, "needs_review", [], [])

    if response.suspicious_instructions:
        logger.warning("ignored instruction-like source content in piece=%s (data only)", piece.id)

    # New classification supersedes the previous current set (history preserved).
    await session.execute(
        update(ContentClassification)
        .where(ContentClassification.content_piece_id == piece.id, ContentClassification.is_current.is_(True))
        .values(is_current=False)
    )

    created: list[uuid.UUID] = []
    for dim_name, dim in result.classifications.items():
        row = ContentClassification(
            project_id=piece.project_id,
            content_piece_id=piece.id,
            classification_dimension=dim_name,
            proposed_value=dim.value,
            approved_value=None,
            origin="ai_proposed",
            confidence=dim.confidence.value,
            reasoning=dim.reasoning,
            evidence_ids=dim.evidence_ids,
            # High-confidence, non-critical proposals auto-accept; the rest need human review.
            review_status="auto_accepted" if dim.confidence.value == "high" else "pending",
            fingerprint=fingerprint,
            is_current=True,
        )
        session.add(row)
        await session.flush()
        created.append(row.id)

    return ClassifyOutcome(piece.id, "classified", created, response.suspicious_instructions)
