"""Readiness checks for /health/ready. Never calls the AI provider (spec §11.1)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import get_sessionmaker


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


async def check_database() -> CheckResult:
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        return CheckResult("database", True, "ok")
    except Exception as exc:  # noqa: BLE001 - report, do not crash readiness
        return CheckResult("database", False, type(exc).__name__)


async def check_redis(settings: Settings) -> CheckResult:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            await asyncio.wait_for(client.ping(), timeout=1.5)
        finally:
            await client.aclose()
        return CheckResult("redis", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("redis", False, type(exc).__name__)


async def check_storage(settings: Settings) -> CheckResult:
    def _probe() -> None:
        from minio import Minio

        client = Minio(
            settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_secure,
        )
        client.bucket_exists(settings.storage_bucket)

    try:
        await asyncio.wait_for(asyncio.to_thread(_probe), timeout=2.0)
        return CheckResult("object_storage", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("object_storage", False, type(exc).__name__)


async def readiness(settings: Settings) -> tuple[bool, list[CheckResult]]:
    results = await asyncio.gather(check_database(), check_redis(settings), check_storage(settings))
    return all(r.ok for r in results), list(results)
