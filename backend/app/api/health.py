from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings
from app.observability.health import readiness

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready")
async def ready(response: Response, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    ok, checks = await readiness(settings)
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ok else "not_ready",
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
    }
