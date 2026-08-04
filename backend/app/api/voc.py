from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.clients.storage import Storage, get_storage
from app.core.config import Settings, get_settings
from app.core.enums import BankType, ClaimType, EvidenceRole, FindingStatus, PaidOrganicStatus, ProofType
from app.db.models.user import User
from app.db.models.voc import Claim, PerformanceRecord, VocEntry
from app.db.session import get_session
from app.services import voc_claims

router = APIRouter(tags=["voc-claims-performance"])


def storage_dep(settings: Settings = Depends(get_settings)) -> Storage:
    return get_storage(settings)


# --- VoC ---
class VocManualIn(BaseModel):
    bank_type: BankType
    verbatim_phrase: str = Field(min_length=1, max_length=2000)
    entity_id: uuid.UUID | None = None


@router.post("/api/v1/projects/{project_id}/voc/manual", status_code=201)
async def voc_manual(
    project_id: uuid.UUID,
    body: VocManualIn,
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(storage_dep),
    user: User = Depends(get_current_user),
) -> dict:
    entry = await voc_claims.add_voc_entry(
        session,
        storage,
        project_id=project_id,
        bank_type=body.bank_type.value,
        verbatim_phrase=body.verbatim_phrase,
        entity_id=body.entity_id,
    )
    await session.commit()
    return {
        "id": str(entry.id),
        "bank_type": entry.bank_type,
        "verbatim_phrase": entry.verbatim_phrase,
        "pattern_key": entry.pattern_key,
        "occurrence_count": entry.occurrence_count,
    }


@router.get("/api/v1/projects/{project_id}/voc")
async def list_voc(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(VocEntry).where(VocEntry.project_id == project_id))).scalars().all()
    return [
        {
            "id": str(e.id),
            "bank_type": e.bank_type,
            "verbatim_phrase": e.verbatim_phrase,
            "occurrence_count": e.occurrence_count,
            "review_status": e.review_status,
        }
        for e in rows
    ]


@router.post("/api/v1/voc/{voc_id}/approve")
async def approve_voc(
    voc_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)
) -> dict:
    e = await session.get(VocEntry, voc_id)
    if e is None:
        raise HTTPException(status_code=404, detail="voc_not_found")
    e.review_status = "approved"
    await session.commit()
    return {"id": str(e.id), "review_status": e.review_status}


@router.get("/api/v1/projects/{project_id}/voc/language-banks")
async def language_banks(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    banks = await voc_claims.language_banks(session, project_id)
    return [
        {
            "bank_type": b.bank_type,
            "phrase_count": b.phrase_count,
            "approved_count": b.approved_count,
            "confidence": b.confidence,
            "confirmed_patterns": b.confirmed_patterns,
        }
        for b in banks
    ]


# --- Claims ---
class ClaimIn(BaseModel):
    entity_id: uuid.UUID
    content_piece_id: uuid.UUID
    claim_text: str = Field(min_length=1, max_length=2000)
    claim_type: ClaimType


@router.post("/api/v1/projects/{project_id}/claims", status_code=201)
async def create_claim(
    project_id: uuid.UUID,
    body: ClaimIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    claim = await voc_claims.add_claim(
        session,
        project_id=project_id,
        entity_id=body.entity_id,
        content_piece_id=body.content_piece_id,
        claim_text=body.claim_text,
        claim_type=body.claim_type.value,
    )
    await session.commit()
    return _claim_out(claim)


def _claim_out(c: Claim) -> dict:
    return {
        "id": str(c.id),
        "claim_text": c.claim_text,
        "claim_type": c.claim_type,
        "proof_status": c.proof_status,
        "finding_status": c.finding_status,
    }


class ClaimEvidenceIn(BaseModel):
    evidence_span_id: uuid.UUID
    proof_type: ProofType
    evidence_role: EvidenceRole
    quality_score: int | None = Field(default=None, ge=0, le=10)


@router.post("/api/v1/claims/{claim_id}/evidence", status_code=201)
async def add_claim_evidence(
    claim_id: uuid.UUID,
    body: ClaimEvidenceIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    claim = await session.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="claim_not_found")
    await voc_claims.attach_claim_evidence(
        session,
        claim=claim,
        evidence_span_id=body.evidence_span_id,
        proof_type=body.proof_type.value,
        evidence_role=body.evidence_role.value,
        quality_score=body.quality_score,
    )
    await session.commit()
    return _claim_out(claim)


class PromoteIn(BaseModel):
    finding_status: FindingStatus


@router.post("/api/v1/claims/{claim_id}/promote")
async def promote_claim(
    claim_id: uuid.UUID,
    body: PromoteIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    claim = await session.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="claim_not_found")
    try:
        await voc_claims.promote_claim_finding_status(session, claim, body.finding_status.value)
    except voc_claims.ClaimPromotionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    return _claim_out(claim)


@router.get("/api/v1/projects/{project_id}/claims")
async def list_claims(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(Claim).where(Claim.project_id == project_id))).scalars().all()
    return [_claim_out(c) for c in rows]


# --- Performance ---
class PerformanceIn(BaseModel):
    entity_id: uuid.UUID
    metric_name: str = Field(min_length=1, max_length=100)
    metric_value: float
    period_start: date
    period_end: date
    paid_organic_status: PaidOrganicStatus
    platform: str | None = None
    spend: float | None = None
    audience_size: float | None = None
    metric_definition: str | None = None
    content_piece_id: uuid.UUID | None = None


@router.post("/api/v1/projects/{project_id}/performance/manual", status_code=201)
async def create_performance(
    project_id: uuid.UUID,
    body: PerformanceIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    record = await voc_claims.add_performance(
        session,
        project_id=project_id,
        entity_id=body.entity_id,
        metric_name=body.metric_name,
        metric_value=body.metric_value,
        period_start=body.period_start,
        period_end=body.period_end,
        paid_organic_status=body.paid_organic_status.value,
        platform=body.platform,
        spend=body.spend,
        audience_size=body.audience_size,
        metric_definition=body.metric_definition,
        content_piece_id=body.content_piece_id,
    )
    await session.commit()
    return {
        "id": str(record.id),
        "metric_name": record.metric_name,
        "is_proxy": record.is_proxy,
        "paid_organic_status": record.paid_organic_status,
    }


@router.get("/api/v1/projects/{project_id}/performance")
async def list_performance(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (await session.execute(select(PerformanceRecord).where(PerformanceRecord.project_id == project_id)))
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "metric_name": r.metric_name,
            "metric_value": float(r.metric_value),
            "is_proxy": r.is_proxy,
            "paid_organic_status": r.paid_organic_status,
        }
        for r in rows
    ]


@router.get("/api/v1/projects/{project_id}/performance/validation")
async def performance_validation(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await voc_claims.performance_validation(session, project_id)
