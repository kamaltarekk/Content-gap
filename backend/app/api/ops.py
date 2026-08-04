from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.pii import UPLOAD_WARNING, redaction_preview
from app.db.models.project import Project
from app.db.models.user import User
from app.db.session import get_session
from app.services import cost_ledger, purge

router = APIRouter(tags=["ops"])


# --- Cost ledger + budget caps -----------------------------------------------------------------


@router.get("/api/v1/projects/{project_id}/cost")
async def get_cost(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await cost_ledger.cost_summary(session, project_id)


class BudgetCapIn(BaseModel):
    budget_cap_usd: float | None = Field(default=None, ge=0)


@router.put("/api/v1/projects/{project_id}/budget-cap")
async def set_budget_cap(
    project_id: uuid.UUID,
    body: BudgetCapIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    project.budget_cap_usd = body.budget_cap_usd
    await session.commit()
    return {"project_id": str(project_id), "budget_cap_usd": body.budget_cap_usd}


# --- PII warning + redaction preview -----------------------------------------------------------


@router.get("/api/v1/pii/warning")
async def pii_warning() -> dict:
    return {"warning": UPLOAD_WARNING}


class RedactionIn(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)


@router.post("/api/v1/pii/redaction-preview")
async def pii_redaction_preview(body: RedactionIn, user: User = Depends(get_current_user)) -> dict:
    return redaction_preview(body.text)


# --- Project purge -----------------------------------------------------------------------------


@router.post("/api/v1/projects/{project_id}/purge")
async def purge_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        result = await purge.purge_project(session, project_id)
    except purge.PurgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return result
