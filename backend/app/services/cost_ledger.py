"""Provider cost ledger + budget caps (spec §24, §31.4).

Every paid provider call is logged with token counts and USD cost; cache hits are logged at zero
cost. A configurable per-project budget cap blocks further paid calls once spend reaches it. No
prompt or evidence text is ever recorded — only counts and identifiers.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import estimate_cost_usd
from app.ai.provider import TokenCount
from app.core.config import Settings, get_settings
from app.db.models.cost_ledger import CostLedgerEntry
from app.db.models.project import Project


class BudgetExceeded(Exception):
    def __init__(self, spent: float, cap: float) -> None:
        super().__init__(f"budget_cap_exceeded:{spent:.4f}/{cap:.4f}")
        self.spent = spent
        self.cap = cap


async def record_cost(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    task: str,
    model: str,
    usage: TokenCount,
    cache_hit: bool = False,
    job_id: uuid.UUID | None = None,
    settings: Settings | None = None,
) -> CostLedgerEntry:
    settings = settings or get_settings()
    cost = 0.0 if cache_hit else estimate_cost_usd(usage.input_tokens, usage.output_tokens, settings)
    entry = CostLedgerEntry(
        project_id=project_id,
        job_id=job_id,
        task=task,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=cost,
        cache_hit=cache_hit,
    )
    session.add(entry)
    await session.flush()
    return entry


async def project_cost(session: AsyncSession, project_id: uuid.UUID) -> float:
    total = (
        await session.execute(
            select(func.coalesce(func.sum(CostLedgerEntry.cost_usd), 0)).where(CostLedgerEntry.project_id == project_id)
        )
    ).scalar_one()
    return float(total)


async def check_budget(session: AsyncSession, project_id: uuid.UUID) -> None:
    """Raise BudgetExceeded if the project has a cap and spend has reached it. Called BEFORE paid
    provider work is enqueued or executed."""
    project = await session.get(Project, project_id)
    if project is None or project.budget_cap_usd is None:
        return
    cap = float(project.budget_cap_usd)
    spent = await project_cost(session, project_id)
    if spent >= cap:
        raise BudgetExceeded(spent, cap)


async def cost_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    entries = (
        (
            await session.execute(
                select(CostLedgerEntry)
                .where(CostLedgerEntry.project_id == project_id)
                .order_by(CostLedgerEntry.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    project = await session.get(Project, project_id)
    return {
        "total_cost_usd": round(sum(float(e.cost_usd) for e in entries), 6),
        "budget_cap_usd": float(project.budget_cap_usd) if project and project.budget_cap_usd is not None else None,
        "call_count": len(entries),
        "cache_hits": sum(1 for e in entries if e.cache_hit),
        "entries": [
            {
                "task": e.task,
                "model": e.model,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "cost_usd": float(e.cost_usd),
                "cache_hit": e.cache_hit,
            }
            for e in entries
        ],
    }
