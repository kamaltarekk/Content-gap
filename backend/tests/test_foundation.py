from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app
from tests.conftest import requires_db


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "live"}


@pytest.mark.asyncio
async def test_readiness_reports_per_dependency(client: AsyncClient) -> None:
    # Redis + object storage are not running in this environment, so readiness must ACCURATELY
    # fail (503) and report which dependency is down (spec Phase 1 acceptance gate).
    r = await client.get("/health/ready")
    body = r.json()
    names = {c["name"] for c in body["checks"]}
    assert names == {"database", "redis", "object_storage"}
    down = [c["name"] for c in body["checks"] if not c["ok"]]
    if down:
        assert r.status_code == 503
        assert body["status"] == "not_ready"
    else:
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_public_config_has_no_secrets(client: AsyncClient) -> None:
    r = await client.get("/api/v1/config/public")
    assert r.status_code == 200
    blob = r.text.lower()
    assert "anthropic" not in blob and "secret" not in blob and "password" not in blob


def test_test_settings_override_real_looking_keys(settings: Settings) -> None:
    # Even if a real-looking key were exported, conftest forces the fake (spec §6.23).
    assert settings.anthropic_api_key == "test-fake-key-not-real"
    assert settings.environment == "test"


@requires_db
@pytest.mark.asyncio
async def test_login_logout_roundtrip(client: AsyncClient) -> None:
    from app.auth.security import hash_password
    from app.db.models.user import User
    from app.db.session import get_sessionmaker

    email = f"user-{uuid.uuid4().hex[:8]}@test.dev"
    async with get_sessionmaker()() as session:
        session.add(User(email=email, password_hash=hash_password("correct-horse"), display_name="T"))
        await session.commit()

    # Not authenticated yet.
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    # Wrong password.
    bad = await client.post("/api/v1/auth/login", json={"email": email, "password": "nope"})
    assert bad.status_code == 401
    # Correct password sets the session cookie.
    ok = await client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse"})
    assert ok.status_code == 200 and ok.json()["email"] == email
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == email
    # Logout clears it.
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401


@requires_db
@pytest.mark.asyncio
async def test_no_auth_mode_provisions_dev_admin(_schema: None) -> None:
    none_settings = get_settings().model_copy(update={"auth_mode": "none"})
    app = create_app(none_settings)
    app.dependency_overrides[get_settings] = lambda: none_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "admin@local.dev"
