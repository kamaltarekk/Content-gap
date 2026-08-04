from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/config/public")
async def public_config(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    """Non-sensitive client configuration. Never exposes secrets or the AI key."""
    return {
        "environment": settings.environment,
        "auth_mode": settings.auth_mode,
        "primary_language_default": "ar",
        "limits": {
            "max_file_mb": 25,
            "max_project_source_mb": 250,
            "max_manual_text_chars": 10000,
            "max_competitors": 3,
            "max_brand_pieces": 200,
            "max_competitor_pieces": 100,
        },
    }
