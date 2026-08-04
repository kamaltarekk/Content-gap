from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import (
    brand_diagnosis,
    buying_group,
    classification,
    context,
    entities,
    health,
    jobs,
    meta,
    projects,
    sources,
    voc,
)
from app.auth import router as auth_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    settings.validate_startup()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Content Diagnosis & Competitive Gap Analysis", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=settings.session_cookie_name,
        https_only=settings.session_https_only,
        same_site="lax",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(auth_router.router)
    app.include_router(projects.router)
    app.include_router(entities.router)
    app.include_router(context.router)
    app.include_router(buying_group.router)
    app.include_router(sources.router)
    app.include_router(jobs.router)
    app.include_router(classification.router)
    app.include_router(voc.router)
    app.include_router(brand_diagnosis.router)
    return app


app = create_app()
