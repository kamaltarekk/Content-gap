"""Competitor collection + observable-only diagnosis (spec §15, §16.4).

Everything here is constrained to public or uploaded evidence:

* Absence is written as "No evidence of X was found in the analyzed public sample", never
  "the competitor does not do X" (spec §6.3).
* Competitor findings are never ``observed_fact`` unless the competitor states it; audience and
  positioning default to inference (spec §15.3).
* Public claims stay claims and commercial performance is never inferred from public proxies
  (spec §15.6).
* Sample sufficiency is computed from bands + modifiers; raw piece count alone can never reach
  ``high`` (spec §16.4).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.storage import Storage
from app.db.models.classification import ContentClassification
from app.db.models.competitor import (
    CompetitorCollection,
    CompetitorCollectionItem,
    CompetitorDiagnosis,
    CompetitorFinding,
)
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.entity import Entity
from app.db.models.voc import Claim, PerformanceRecord, VocEntry
from app.services import ingest

LIMITATION_BANNER = (
    "This diagnosis is based only on the public or uploaded sources collected for the stated "
    "period. It does not represent the competitor's private sales process, internal data, "
    "profitability, or complete content system."
)

# Observable presence checklist. Each topic maps to the classification value that evidences it, so
# absence can be reported honestly as not_found_in_sample.
_PRESENCE_TOPICS: dict[str, str] = {
    "pricing": "offer",
    "proof": "claim_proof",
    "comparison": "comparison",
    "authority": "authority",
}


class CompetitorError(Exception):
    pass


@dataclass
class CollectionItemInput:
    content_format: str
    text: str | None = None
    url: str | None = None
    status: str | None = None  # explicit 'blocked'/'failed' for URLs that could not be fetched


def _downgrade(level: str) -> str:
    ladder = ["low", "medium", "high"]
    if level not in ladder:
        return level
    return ladder[max(0, ladder.index(level) - 1)]


def sample_sufficiency(collected: int, channels: list[str], duplicate_rate: float, extraction_low: bool = False) -> str:
    """Sufficiency label from piece-count bands then modifiers (spec §16.4). Piece count alone can
    never yield 'high' — a single-channel sample is capped at 'medium' regardless of volume."""
    if collected == 0:
        return "insufficient_evidence"
    level = "high" if collected >= 40 else "medium" if collected >= 15 else "low"
    if duplicate_rate > 0.3:
        level = _downgrade(level)
    if extraction_low:
        level = _downgrade(level)
    # A single channel cannot demonstrate breadth, so it can never reach 'high'.
    if len({c for c in channels if c}) < 2 and level == "high":
        level = "medium"
    return level


async def _competitor(session: AsyncSession, project_id: uuid.UUID, entity_id: uuid.UUID) -> Entity:
    entity = await session.get(Entity, entity_id)
    if entity is None or entity.project_id != project_id or entity.entity_type != "competitor":
        raise CompetitorError("competitor_not_found")
    if not (entity.comparison_rationale and entity.comparison_rationale.strip()):
        raise CompetitorError("comparison_rationale_required")
    return entity


async def collect_competitor(
    session: AsyncSession,
    storage: Storage,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID,
    items: list[CollectionItemInput],
    channels: list[str] | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> CompetitorCollection:
    await _competitor(session, project_id, entity_id)
    collection = CompetitorCollection(
        project_id=project_id,
        entity_id=entity_id,
        requested_count=len(items),
        channels=channels or [],
        period_start=period_start,
        period_end=period_end,
    )
    session.add(collection)
    await session.flush()

    collected_pieces: list[uuid.UUID] = []
    blocked = failed = 0
    for item in items:
        explicit = item.status in ("blocked", "failed")
        if explicit or item.text is None:
            status = item.status or "blocked"
            if status == "failed":
                failed += 1
            else:
                blocked += 1
            reason = f"url {status}" if item.status else "no content extracted"
            session.add(
                CompetitorCollectionItem(collection_id=collection.id, url=item.url, item_status=status, reason=reason)
            )
            continue
        result = await ingest.ingest_manual_text(
            session,
            storage,
            project_id=project_id,
            entity_id=entity_id,
            source_category="competitor_public",
            display_name=item.url or "competitor",
            text=item.text,
            content_format=item.content_format,
            user_id=None,
        )
        piece_id = result.content_piece_ids[0]
        collected_pieces.append(piece_id)
        session.add(
            CompetitorCollectionItem(
                collection_id=collection.id, url=item.url, item_status="collected", content_piece_id=piece_id
            )
        )

    collected = len(collected_pieces)
    # Duplicate rate over collected pieces (reposts do not increase coverage, spec §16.2).
    dup = 0
    if collected_pieces:
        rows = (
            (await session.execute(select(ContentPiece).where(ContentPiece.id.in_(collected_pieces)))).scalars().all()
        )
        dup = sum(1 for p in rows if not p.is_canonical)
    collection.collected_count = collected
    collection.blocked_count = blocked
    collection.failed_count = failed
    collection.duplicate_rate = (dup / collected) if collected else 0
    if collected == 0:
        collection.status = "empty"
    elif blocked or failed or collected < len(items):
        collection.status = "partial"
    else:
        collection.status = "complete"
    await session.flush()
    return collection


@dataclass
class _Finding:
    dimension: str
    subject: str
    summary: str
    presence: str = "unknown"
    finding_status: str = "inference"
    confidence: str = "low"
    is_public_proxy: bool = False
    evidence_span_ids: list[str] = field(default_factory=list)


async def run_competitor_diagnosis(
    session: AsyncSession, project_id: uuid.UUID, entity_id: uuid.UUID
) -> CompetitorDiagnosis:
    await _competitor(session, project_id, entity_id)

    collection = (
        await session.execute(
            select(CompetitorCollection)
            .where(CompetitorCollection.entity_id == entity_id)
            .order_by(CompetitorCollection.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    pieces = (
        (
            await session.execute(
                select(ContentPiece).where(
                    ContentPiece.project_id == project_id,
                    ContentPiece.entity_id == entity_id,
                    ContentPiece.is_canonical.is_(True),
                    ContentPiece.include_in_analysis.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    piece_ids = {p.id for p in pieces}

    span_by_piece: dict[uuid.UUID, uuid.UUID] = {}
    if piece_ids:
        for span in (
            (await session.execute(select(EvidenceSpan).where(EvidenceSpan.content_piece_id.in_(piece_ids))))
            .scalars()
            .all()
        ):
            span_by_piece.setdefault(span.content_piece_id, span.id)

    if collection is not None:
        sufficiency = sample_sufficiency(
            collection.collected_count, list(collection.channels or []), float(collection.duplicate_rate)
        )
        channels = list(collection.channels or [])
    else:
        # No manifest: judge from what is on hand, but a single/unknown channel is capped at medium.
        sufficiency = sample_sufficiency(len(pieces), [], 0.0)
        channels = []

    # Effective classification value per competitor piece.
    element_rows = (
        (
            await session.execute(
                select(ContentClassification).where(
                    ContentClassification.project_id == project_id,
                    ContentClassification.classification_dimension == "primary_sales_element",
                    ContentClassification.is_current.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    present_elements: dict[str, list[uuid.UUID]] = {}
    for r in element_rows:
        if r.content_piece_id in piece_ids:
            val = r.approved_value or r.proposed_value
            if val:
                present_elements.setdefault(val, []).append(r.content_piece_id)

    comp_claims = (
        (await session.execute(select(Claim).where(Claim.project_id == project_id, Claim.entity_id == entity_id)))
        .scalars()
        .all()
    )

    findings: list[_Finding] = []

    # --- Presence checklist (honest absence) ---------------------------------------------------
    presence_audit: list[dict] = []
    for topic, element in _PRESENCE_TOPICS.items():
        covering = present_elements.get(element, [])
        has_priced_claim = topic == "pricing" and any(c.claim_type == "price" for c in comp_claims)
        found = bool(covering) or has_priced_claim
        presence = "found" if found else "not_found_in_sample"
        ev = [str(span_by_piece[p]) for p in covering if p in span_by_piece]
        presence_audit.append({"topic": topic, "presence": presence, "evidence_span_ids": ev})
        findings.append(
            _Finding(
                dimension="coverage",
                subject=topic,
                presence=presence,
                confidence="low",
                summary=(
                    f"Evidence of {topic} was found in the analyzed public sample."
                    if found
                    else f"No evidence of {topic} was found in the analyzed public sample."
                ),
                evidence_span_ids=ev,
            )
        )

    # --- Audience / positioning: inference only (spec §15.3) -----------------------------------
    findings.append(
        _Finding(
            dimension="audience",
            subject="audience_positioning",
            presence="unknown",
            finding_status="inference",
            confidence="low",
            summary="Audience and positioning are inferred from public content, not observed facts.",
        )
    )

    # --- Competitor claim–proof: a public claim remains a claim --------------------------------
    for claim in comp_claims:
        findings.append(
            _Finding(
                dimension="claim_proof",
                subject=claim.claim_text[:200],
                presence="found",
                finding_status="brand_claim",  # never observed_fact from public evidence
                confidence="low",
                summary=f"Public claim '{claim.claim_text}' remains a claim; public evidence cannot confirm it.",
            )
        )

    # --- Observable authority maturity: public proxies only ------------------------------------
    recurring_formats = len({p.content_format for p in pieces})
    findings.append(
        _Finding(
            dimension="authority_maturity",
            subject="authority_signals",
            presence="found" if pieces else "unknown",
            finding_status="inference",
            confidence="low",
            is_public_proxy=True,
            summary=(
                f"Observable authority signals are public proxies only ({recurring_formats} recurring "
                "format(s)); this is not owner readiness."
            ),
        )
    )

    # --- Competitor VoC leak map ---------------------------------------------------------------
    leaks = (
        (
            await session.execute(
                select(VocEntry).where(
                    VocEntry.project_id == project_id,
                    VocEntry.entity_id == entity_id,
                    VocEntry.bank_type.in_(("complaint", "switching_reason", "question")),
                )
            )
        )
        .scalars()
        .all()
    )
    for leak in leaks:
        findings.append(
            _Finding(
                dimension="voc_leak",
                subject=leak.bank_type,
                presence="found",
                finding_status="inference",
                confidence="low",
                summary=(
                    f"Public leak ({leak.bank_type}): '{leak.verbatim_phrase}'. An opportunity only if "
                    "the brand can credibly perform better and provide proof."
                ),
                evidence_span_ids=[str(leak.evidence_span_id)],
            )
        )

    # --- Performance: public proxies only, never inferred commercial outcomes ------------------
    perf = (
        (
            await session.execute(
                select(PerformanceRecord).where(
                    PerformanceRecord.project_id == project_id, PerformanceRecord.entity_id == entity_id
                )
            )
        )
        .scalars()
        .all()
    )
    if perf:
        findings.append(
            _Finding(
                dimension="performance",
                subject="public_proxies",
                presence="found",
                finding_status="inference",
                confidence="low",
                is_public_proxy=True,
                summary=(
                    "Only public engagement proxies are observable. Commercial performance "
                    "(conversion, CAC, profit, retention) cannot be inferred from them."
                ),
            )
        )

    diagnosis = CompetitorDiagnosis(
        project_id=project_id,
        entity_id=entity_id,
        collection_id=collection.id if collection else None,
        sample_sufficiency=sufficiency,
        sample_piece_count=len(pieces),
        limitation_banner=LIMITATION_BANNER,
        audits={
            "sample": {
                "sufficiency": sufficiency,
                "piece_count": len(pieces),
                "channels": channels,
                "collection_status": collection.status if collection else None,
                "blocked": collection.blocked_count if collection else 0,
                "failed": collection.failed_count if collection else 0,
            },
            "content_cards": [
                {
                    "content_piece_id": str(p.id),
                    "content_format": p.content_format,
                    "snippet": p.original_text[:120],
                    "evidence_span_id": str(span_by_piece[p.id]) if p.id in span_by_piece else None,
                }
                for p in pieces
            ],
            "presence": presence_audit,
            "performance": {"has_direct_outcome": False, "proxy_only": True},
        },
    )
    session.add(diagnosis)
    await session.flush()

    for f in findings:
        # Invariant: competitor evidence never yields an observed fact.
        assert f.finding_status != "observed_fact"
        session.add(
            CompetitorFinding(
                diagnosis_id=diagnosis.id,
                project_id=project_id,
                entity_id=entity_id,
                dimension=f.dimension,
                subject=f.subject,
                presence=f.presence,
                finding_status=f.finding_status,
                confidence=f.confidence,
                is_public_proxy=f.is_public_proxy,
                summary=f.summary,
                evidence_span_ids=f.evidence_span_ids,
            )
        )
    await session.flush()
    return diagnosis


async def get_diagnosis_payload(session: AsyncSession, diagnosis_id: uuid.UUID) -> dict:
    diagnosis = await session.get(CompetitorDiagnosis, diagnosis_id)
    if diagnosis is None:
        raise CompetitorError("diagnosis_not_found")
    findings = (
        (await session.execute(select(CompetitorFinding).where(CompetitorFinding.diagnosis_id == diagnosis_id)))
        .scalars()
        .all()
    )
    return {
        "id": str(diagnosis.id),
        "project_id": str(diagnosis.project_id),
        "entity_id": str(diagnosis.entity_id),
        "limitation_banner": diagnosis.limitation_banner,  # shown on every competitor view (§15.1)
        "sample_sufficiency": diagnosis.sample_sufficiency,
        "sample_piece_count": diagnosis.sample_piece_count,
        "audits": diagnosis.audits,
        "findings": [
            {
                "id": str(f.id),
                "dimension": f.dimension,
                "subject": f.subject,
                "presence": f.presence,
                "finding_status": f.finding_status,
                "confidence": f.confidence,
                "is_public_proxy": f.is_public_proxy,
                "summary": f.summary,
                "evidence_span_ids": f.evidence_span_ids,
            }
            for f in findings
        ],
    }


async def get_collection_payload(collection: CompetitorCollection, session: AsyncSession) -> dict:
    items = (
        (
            await session.execute(
                select(CompetitorCollectionItem).where(CompetitorCollectionItem.collection_id == collection.id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "id": str(collection.id),
        "entity_id": str(collection.entity_id),
        "status": collection.status,
        "requested_count": collection.requested_count,
        "collected_count": collection.collected_count,
        "blocked_count": collection.blocked_count,
        "failed_count": collection.failed_count,
        "duplicate_rate": float(collection.duplicate_rate),
        "channels": collection.channels,
        "items": [
            {
                "url": i.url,
                "item_status": i.item_status,
                "reason": i.reason,
                "content_piece_id": str(i.content_piece_id) if i.content_piece_id else None,
            }
            for i in items
        ],
    }
