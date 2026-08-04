"""VoC, claims/proof, and performance services. Deterministic rules keep everything traceable and
prevent promotion from proxy/claim to fact without evidence (spec §4.6, §4.20, §4.21, §6.19)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.storage import Storage
from app.core.config import get_settings
from app.core.text import normalize_for_hash, sha256_text
from app.db.models.content_piece import EvidenceSpan
from app.db.models.voc import Claim, ClaimEvidence, PerformanceRecord, VocEntry
from app.services import ingest

# Visible-engagement metrics are proxies only (spec §6.21); direct commercial outcomes are not.
_PROXY_METRICS = {
    "views",
    "likes",
    "impressions",
    "reach",
    "engagement",
    "saves",
    "shares",
    "comments",
    "followers",
    "watch_time",
}
_COMMERCIAL_METRICS = {"conversions", "revenue", "sales", "orders", "purchases", "leads", "signups", "cac"}


def metric_is_proxy(metric_name: str) -> bool:
    name = metric_name.strip().lower()
    if name in _COMMERCIAL_METRICS:
        return False
    # Known engagement metrics and any unknown metric are treated as proxies — never promoted to
    # a commercial fact without explicit evidence.
    return True


# --- Voice of Customer -------------------------------------------------------------------------


async def add_voc_entry(
    session: AsyncSession,
    storage: Storage,
    *,
    project_id: uuid.UUID,
    bank_type: str,
    verbatim_phrase: str,
    entity_id: uuid.UUID | None = None,
) -> VocEntry:
    # Every VoC entry needs a traceable content piece + evidence span. Manual entries ingest the
    # verbatim phrase as a customer_voice source; the phrase is stored EXACTLY, never rewritten.
    result = await ingest.ingest_manual_text(
        session,
        storage,
        project_id=project_id,
        entity_id=entity_id,
        source_category="customer_voice",
        display_name="voc",
        text=verbatim_phrase,
        content_format="comment",
        user_id=None,
    )
    piece_id = result.content_piece_ids[0]
    span = (
        await session.execute(select(EvidenceSpan).where(EvidenceSpan.content_piece_id == piece_id).limit(1))
    ).scalar_one()

    pattern_key = sha256_text(normalize_for_hash(verbatim_phrase))
    entry = VocEntry(
        project_id=project_id,
        entity_id=entity_id,
        content_piece_id=piece_id,
        evidence_span_id=span.id,
        bank_type=bank_type,
        verbatim_phrase=verbatim_phrase,
        pattern_key=pattern_key,
    )
    session.add(entry)
    await session.flush()

    # Repetition detection: keep every row's occurrence_count = total for its pattern in the project.
    count = len(
        (
            await session.execute(
                select(VocEntry.id).where(VocEntry.project_id == project_id, VocEntry.pattern_key == pattern_key)
            )
        ).all()
    )
    await session.execute(
        update(VocEntry)
        .where(VocEntry.project_id == project_id, VocEntry.pattern_key == pattern_key)
        .values(occurrence_count=count)
    )
    entry.occurrence_count = count
    return entry


@dataclass
class BankSummary:
    bank_type: str
    phrase_count: int
    approved_count: int
    confidence: str
    confirmed_patterns: list[str]


async def language_banks(session: AsyncSession, project_id: uuid.UUID) -> list[BankSummary]:
    settings = get_settings()
    rows = (await session.execute(select(VocEntry).where(VocEntry.project_id == project_id))).scalars().all()
    banks: dict[str, list[VocEntry]] = {}
    for r in rows:
        banks.setdefault(r.bank_type, []).append(r)
    summaries: list[BankSummary] = []
    for bank_type, entries in banks.items():
        approved = [e for e in entries if e.review_status == "approved"]
        pattern_counts: dict[str, int] = {}
        for e in entries:
            if e.pattern_key:
                pattern_counts[e.pattern_key] = pattern_counts.get(e.pattern_key, 0) + 1
        confirmed = [k for k, c in pattern_counts.items() if c >= settings.voc_pattern_confirm_min]
        # High confidence requires at least N approved real phrases (spec §10.13).
        confidence = "high" if len(approved) >= settings.voc_high_confidence_min_phrases else "low"
        summaries.append(BankSummary(bank_type, len(entries), len(approved), confidence, confirmed))
    return summaries


# --- Claims & proof ----------------------------------------------------------------------------


async def add_claim(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID,
    content_piece_id: uuid.UUID,
    claim_text: str,
    claim_type: str,
) -> Claim:
    # A claim starts UNSUPPORTED; it becomes proven only when supporting evidence is attached.
    claim = Claim(
        project_id=project_id,
        entity_id=entity_id,
        content_piece_id=content_piece_id,
        claim_text=claim_text,
        claim_type=claim_type,
        proof_status="unsupported",
        finding_status="brand_claim",
    )
    session.add(claim)
    await session.flush()
    return claim


async def attach_claim_evidence(
    session: AsyncSession,
    *,
    claim: Claim,
    evidence_span_id: uuid.UUID,
    proof_type: str,
    evidence_role: str,
    quality_score: int | None = None,
) -> None:
    session.add(
        ClaimEvidence(
            claim_id=claim.id,
            evidence_span_id=evidence_span_id,
            proof_type=proof_type,
            evidence_role=evidence_role,
            quality_score=quality_score,
        )
    )
    await session.flush()
    await _recompute_proof_status(session, claim)


async def _recompute_proof_status(session: AsyncSession, claim: Claim) -> None:
    rows = (await session.execute(select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id))).scalars().all()
    roles = {r.evidence_role for r in rows}
    supports = [r for r in rows if r.evidence_role == "supports"]
    if "contradicts" in roles:
        claim.proof_status = "contradicted"
    elif not supports:
        claim.proof_status = "unsupported"
    elif any((r.quality_score or 0) >= 7 and r.proof_type not in ("visible_proxy", "none") for r in supports):
        claim.proof_status = "proven"
    else:
        claim.proof_status = "partially_proven"


class ClaimPromotionError(Exception):
    pass


async def promote_claim_finding_status(session: AsyncSession, claim: Claim, finding_status: str) -> None:
    # A claim cannot be promoted to observed_fact without supporting evidence (the gate).
    if finding_status == "observed_fact":
        supports = (
            (
                await session.execute(
                    select(ClaimEvidence).where(
                        ClaimEvidence.claim_id == claim.id, ClaimEvidence.evidence_role == "supports"
                    )
                )
            )
            .scalars()
            .all()
        )
        if not supports:
            raise ClaimPromotionError("cannot_promote_claim_to_fact_without_supporting_evidence")
    claim.finding_status = finding_status


# --- Performance -------------------------------------------------------------------------------


async def add_performance(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID,
    metric_name: str,
    metric_value: float,
    period_start: date,
    period_end: date,
    paid_organic_status: str,
    platform: str | None = None,
    spend: float | None = None,
    audience_size: float | None = None,
    metric_definition: str | None = None,
    content_piece_id: uuid.UUID | None = None,
) -> PerformanceRecord:
    record = PerformanceRecord(
        project_id=project_id,
        entity_id=entity_id,
        content_piece_id=content_piece_id,
        metric_name=metric_name,
        metric_value=metric_value,
        period_start=period_start,
        period_end=period_end,
        platform=platform,
        paid_organic_status=paid_organic_status,
        spend=spend,
        audience_size=audience_size,
        metric_definition=metric_definition,
        is_proxy=metric_is_proxy(metric_name),
    )
    session.add(record)
    await session.flush()
    return record


async def performance_validation(session: AsyncSession, project_id: uuid.UUID) -> dict:
    rows = (
        (await session.execute(select(PerformanceRecord).where(PerformanceRecord.project_id == project_id)))
        .scalars()
        .all()
    )
    warnings: list[str] = []
    by_metric: dict[str, list[PerformanceRecord]] = {}
    for r in rows:
        by_metric.setdefault(r.metric_name, []).append(r)
    for metric, recs in by_metric.items():
        periods = {(r.period_start.isoformat(), r.period_end.isoformat()) for r in recs}
        if len(periods) > 1:
            warnings.append(f"incompatible_periods:{metric} cannot be aggregated without normalization/approval")
        statuses = {r.paid_organic_status for r in recs}
        if {"paid", "organic"} <= statuses:
            warnings.append(f"paid_and_organic_mixed:{metric} must be separated")
    return {
        "record_count": len(rows),
        "proxy_count": sum(1 for r in rows if r.is_proxy),
        "commercial_count": sum(1 for r in rows if not r.is_proxy),
        "paid": [str(r.id) for r in rows if r.paid_organic_status == "paid"],
        "organic": [str(r.id) for r in rows if r.paid_organic_status == "organic"],
        "warnings": warnings,
    }
