from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.audit import write_audit
from app.core.enums import BuyingGroupRole, PrimaryBottleneck, PurchaseType
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.project import Project
from app.db.models.user import User
from app.db.session import get_session
from app.rules.preconditions import evaluate_prerequisites

router = APIRouter(tags=["context"])

_MUTABLE_FIELDS = (
    "target_buying_decision",
    "purchase_type",
    "primary_product_or_service",
    "primary_segment_name",
    "primary_segment_definition",
    "primary_decision_maker_role",
    "primary_decision_maker_label",
    "commercial_value_notes",
    "commercial_value_amount",
    "commercial_value_currency",
    "primary_bottleneck",
    "bottleneck_statement",
    "attention_score",
    "attention_reasoning",
    "desire_score",
    "desire_reasoning",
    "persuasion_score",
    "persuasion_reasoning",
    "friction_summary",
    "score_evidence",
    "analysis_period_start",
    "analysis_period_end",
    "comparison_period_start",
    "comparison_period_end",
    "included_channels",
)


class ContextCreate(BaseModel):
    target_buying_decision: str = Field(min_length=1)
    purchase_type: PurchaseType
    primary_product_or_service: str = Field(min_length=1)
    primary_segment_name: str = Field(min_length=1, max_length=300)
    primary_segment_definition: str = Field(min_length=1)
    primary_decision_maker_role: BuyingGroupRole
    primary_decision_maker_label: str | None = None
    commercial_value_notes: str | None = None
    commercial_value_amount: float | None = None
    commercial_value_currency: str | None = Field(default=None, max_length=3)
    primary_bottleneck: PrimaryBottleneck
    bottleneck_statement: str = Field(min_length=1)
    attention_score: int | None = Field(default=None, ge=1, le=10)
    attention_reasoning: str | None = None
    desire_score: int | None = Field(default=None, ge=1, le=10)
    desire_reasoning: str | None = None
    persuasion_score: int | None = Field(default=None, ge=1, le=10)
    persuasion_reasoning: str | None = None
    friction_summary: str | None = None
    score_evidence: dict[str, list[str]] = Field(default_factory=dict)
    analysis_period_start: date | None = None
    analysis_period_end: date | None = None
    comparison_period_start: date | None = None
    comparison_period_end: date | None = None
    included_channels: list[str] = Field(default_factory=list)


class ContextUpdate(ContextCreate):
    # Same fields, all optional for PATCH.
    target_buying_decision: str | None = None  # type: ignore[assignment]
    purchase_type: PurchaseType | None = None  # type: ignore[assignment]
    primary_product_or_service: str | None = None  # type: ignore[assignment]
    primary_segment_name: str | None = None  # type: ignore[assignment]
    primary_segment_definition: str | None = None  # type: ignore[assignment]
    primary_decision_maker_role: BuyingGroupRole | None = None  # type: ignore[assignment]
    primary_bottleneck: PrimaryBottleneck | None = None  # type: ignore[assignment]
    bottleneck_statement: str | None = None  # type: ignore[assignment]


def _serialize(c: DiagnosticContextVersion) -> dict:
    return {f: getattr(c, f) for f in _MUTABLE_FIELDS} | {
        "id": str(c.id),
        "project_id": str(c.project_id),
        "version_number": c.version_number,
        "status": c.status,
        "approved_at": c.approved_at.isoformat() if c.approved_at else None,
    }


async def _next_version(session: AsyncSession, project_id: uuid.UUID) -> int:
    current = (
        await session.execute(
            select(func.max(DiagnosticContextVersion.version_number)).where(
                DiagnosticContextVersion.project_id == project_id
            )
        )
    ).scalar()
    return (current or 0) + 1


async def _has_primary_brand(session: AsyncSession, project_id: uuid.UUID) -> bool:
    row = (
        await session.execute(
            select(Entity.id).where(Entity.project_id == project_id, Entity.is_primary_brand.is_(True)).limit(1)
        )
    ).first()
    return row is not None


def _coerce_enum(data: dict) -> dict:
    for key in ("purchase_type", "primary_decision_maker_role", "primary_bottleneck"):
        if key in data and data[key] is not None and hasattr(data[key], "value"):
            data[key] = data[key].value
    return data


@router.post("/api/v1/projects/{project_id}/context/versions", status_code=201)
async def create_context(
    project_id: uuid.UUID,
    body: ContextCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    if await session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    data = _coerce_enum(body.model_dump())
    c = DiagnosticContextVersion(
        project_id=project_id, version_number=await _next_version(session, project_id), created_by=user.id, **data
    )
    session.add(c)
    await session.flush()
    await write_audit(
        session,
        action="create",
        object_type="context_version",
        object_id=str(c.id),
        project_id=project_id,
        user_id=user.id,
        metadata={"version": c.version_number},
    )
    await session.commit()
    await session.refresh(c)
    return _serialize(c)


@router.get("/api/v1/projects/{project_id}/context/versions")
async def list_context(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(DiagnosticContextVersion)
                .where(DiagnosticContextVersion.project_id == project_id)
                .order_by(DiagnosticContextVersion.version_number)
            )
        )
        .scalars()
        .all()
    )
    return [_serialize(c) for c in rows]


async def _get_ctx(session: AsyncSession, version_id: uuid.UUID) -> DiagnosticContextVersion:
    c = await session.get(DiagnosticContextVersion, version_id)
    if c is None:
        raise HTTPException(status_code=404, detail="context_version_not_found")
    return c


@router.get("/api/v1/context/versions/{version_id}")
async def get_context(version_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return _serialize(await _get_ctx(session, version_id))


@router.patch("/api/v1/context/versions/{version_id}")
async def patch_context(
    version_id: uuid.UUID,
    body: ContextUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    c = await _get_ctx(session, version_id)
    if c.status == "approved":
        raise HTTPException(status_code=409, detail="approved_context_is_immutable_clone_to_edit")
    data = _coerce_enum(body.model_dump(exclude_unset=True))
    for k, v in data.items():
        setattr(c, k, v)
    await write_audit(
        session,
        action="update",
        object_type="context_version",
        object_id=str(c.id),
        project_id=c.project_id,
        user_id=user.id,
        metadata={"fields": sorted(data)},
    )
    await session.commit()
    await session.refresh(c)
    return _serialize(c)


@router.post("/api/v1/context/versions/{version_id}/validate")
async def validate_context(version_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    c = await _get_ctx(session, version_id)
    project = await session.get(Project, c.project_id)
    result = evaluate_prerequisites(
        _serialize(c),
        project_name=project.name if project else None,
        has_primary_brand=await _has_primary_brand(session, c.project_id),
    )
    return result.as_dict()


@router.post("/api/v1/context/versions/{version_id}/approve")
async def approve_context(
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    c = await _get_ctx(session, version_id)
    if c.status == "approved":
        return _serialize(c)
    project = await session.get(Project, c.project_id)
    gate = evaluate_prerequisites(
        _serialize(c),
        project_name=project.name if project else None,
        has_primary_brand=await _has_primary_brand(session, c.project_id),
    )
    if not gate.can_run_full_analysis:
        raise HTTPException(status_code=422, detail={"code": "PREREQUISITES_INCOMPLETE", "gate": gate.as_dict()})
    c.status = "approved"
    c.approved_by = user.id
    c.approved_at = datetime.now(UTC)
    await write_audit(
        session,
        action="approve",
        object_type="context_version",
        object_id=str(c.id),
        project_id=c.project_id,
        user_id=user.id,
        metadata={"version": c.version_number},
    )
    await session.commit()
    await session.refresh(c)
    return _serialize(c)


@router.post("/api/v1/context/versions/{version_id}/clone", status_code=201)
async def clone_context(
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    src = await _get_ctx(session, version_id)
    clone = DiagnosticContextVersion(
        project_id=src.project_id,
        version_number=await _next_version(session, src.project_id),
        created_by=user.id,
        status="pending",
        **{f: getattr(src, f) for f in _MUTABLE_FIELDS},
    )
    session.add(clone)
    await session.flush()
    await write_audit(
        session,
        action="clone",
        object_type="context_version",
        object_id=str(clone.id),
        project_id=src.project_id,
        user_id=user.id,
        metadata={"from_version": src.version_number, "to_version": clone.version_number},
    )
    await session.commit()
    await session.refresh(clone)
    return _serialize(clone)
