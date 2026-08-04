from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import estimate_cost_usd
from app.auth.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.enums import ReviewStatus
from app.db.models.classification import ContentClassification
from app.db.models.content_piece import ContentPiece
from app.db.models.user import User
from app.db.session import get_session
from app.jobs import service
from app.jobs.dispatcher import Dispatcher, get_dispatcher
from app.services import cost_ledger

router = APIRouter(tags=["classification"])

_AVG_INPUT_TOKENS = 700
_AVG_OUTPUT_TOKENS = 200


def dispatcher_dep(settings: Settings = Depends(get_settings)) -> Dispatcher:
    return get_dispatcher(settings)


@router.post("/api/v1/projects/{project_id}/classification/estimate")
async def estimate(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    count = (
        await session.execute(
            select(func.count())
            .select_from(ContentPiece)
            .where(
                ContentPiece.project_id == project_id,
                ContentPiece.include_in_analysis.is_(True),
                ContentPiece.is_canonical.is_(True),
            )
        )
    ).scalar_one()
    input_tokens = count * _AVG_INPUT_TOKENS
    output_tokens = count * _AVG_OUTPUT_TOKENS
    return {
        "content_piece_count": count,
        "expected_provider_operations": count,
        "estimated_cost": {
            "amount": estimate_cost_usd(input_tokens, output_tokens, settings),
            "currency": "USD",
            "is_estimate": True,
        },
        "cache_available": True,
        "excluded_non_canonical_or_excluded": True,
    }


class RunIn(BaseModel):
    context_version_id: uuid.UUID | None = None


@router.post("/api/v1/projects/{project_id}/classification/run", status_code=202)
async def run(
    project_id: uuid.UUID,
    body: RunIn,
    session: AsyncSession = Depends(get_session),
    dispatcher: Dispatcher = Depends(dispatcher_dep),
    user: User = Depends(get_current_user),
) -> dict:
    # Budget cap: block paid classification once the project's cap is reached (spec §31.4).
    try:
        await cost_ledger.check_budget(session, project_id)
    except cost_ledger.BudgetExceeded as exc:
        raise HTTPException(status_code=402, detail=f"budget_cap_exceeded:{exc.spent:.4f}/{exc.cap:.4f}") from exc
    job, created = await service.enqueue_job(
        session,
        project_id=project_id,
        job_type="classify_content",
        input_manifest={
            "project_id": str(project_id),
            "context_version_id": str(body.context_version_id) if body.context_version_id else "",
        },
    )
    await session.commit()
    if created:
        dispatcher.dispatch(job.id)
    return {"job_id": str(job.id), "status": job.status, "cache_hit": not created}


def _out(c: ContentClassification) -> dict:
    return {
        "id": str(c.id),
        "content_piece_id": str(c.content_piece_id),
        "dimension": c.classification_dimension,
        "proposed_value": c.proposed_value,
        "approved_value": c.approved_value,
        "origin": c.origin,
        "confidence": c.confidence,
        "review_status": c.review_status,
        "evidence_ids": c.evidence_ids,
        "is_current": c.is_current,
    }


@router.get("/api/v1/projects/{project_id}/classification/review-queue")
async def review_queue(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(ContentClassification).where(
                    ContentClassification.project_id == project_id,
                    ContentClassification.review_status == "pending",
                    ContentClassification.is_current.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    return [_out(c) for c in rows]


@router.get("/api/v1/content/{content_piece_id}/classifications")
async def content_classifications(
    content_piece_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(ContentClassification)
                .where(ContentClassification.content_piece_id == content_piece_id)
                .order_by(ContentClassification.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [_out(c) for c in rows]


class ReviewIn(BaseModel):
    decision: ReviewStatus
    approved_value: str | None = None
    reason: str | None = Field(default=None, max_length=2000)


async def _apply_review(session: AsyncSession, c: ContentClassification, body: ReviewIn, user: User) -> None:
    # Human decision stored separately; the AI proposal is never overwritten (spec §6.27).
    c.review_status = body.decision.value
    c.reviewed_by = user.id
    c.reviewed_at = datetime.now(UTC)
    if body.decision == ReviewStatus.approved:
        c.approved_value = body.approved_value if body.approved_value is not None else c.proposed_value


@router.post("/api/v1/classifications/{classification_id}/review")
async def review_one(
    classification_id: uuid.UUID,
    body: ReviewIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    c = await session.get(ContentClassification, classification_id)
    if c is None:
        raise HTTPException(status_code=404, detail="classification_not_found")
    await _apply_review(session, c, body, user)
    await session.commit()
    return _out(c)


class BulkReviewIn(BaseModel):
    classification_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    decision: ReviewStatus


@router.post("/api/v1/classifications/bulk-review")
async def bulk_review(
    body: BulkReviewIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    updated = 0
    for cid in body.classification_ids:
        c = await session.get(ContentClassification, cid)
        if c is None:
            continue
        await _apply_review(session, c, ReviewIn(decision=body.decision), user)
        updated += 1
    await session.commit()
    return {"updated": updated}
