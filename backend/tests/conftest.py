from __future__ import annotations

import os

# Force offline/test configuration BEFORE any app import (spec §6.23): even if the developer
# has real provider keys in the shell, tests must use fakes and a test database.
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "AUTH_MODE": "session",
        "SESSION_SECRET": "test-secret",
        "DATABASE_URL": "postgresql+asyncpg://cgi:cgi@localhost:5433/cdga_test",
        "REDIS_URL": "redis://localhost:6390/0",
        "AI_PROVIDER": "fake",
        "ANTHROPIC_API_KEY": "test-fake-key-not-real",
        "ANTHROPIC_MODEL": "claude-sonnet-5",
    }
)

from collections.abc import AsyncIterator, Iterator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

import app.db.session as db_session  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import user as _user  # noqa: E402,F401
from app.main import create_app  # noqa: E402


def _db_reachable() -> bool:
    import socket

    try:
        socket.create_connection(("localhost", 5433), timeout=1).close()
        return True
    except OSError:
        return False


DB_AVAILABLE = _db_reachable()
requires_db = pytest.mark.skipif(not DB_AVAILABLE, reason="Postgres not reachable on :5433")


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    """Create/drop tables with a SYNC engine (no event loop) to avoid asyncpg loop binding."""
    if not DB_AVAILABLE:
        yield
        return
    engine = create_engine(get_settings().alembic_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    yield
    engine = create_engine(get_settings().alembic_url)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _isolate_async_engine() -> Iterator[None]:
    """Give each test its own async engine bound to its own event loop (asyncpg requirement)."""
    db_session._engine = None
    db_session._sessionmaker = None
    yield
    db_session._engine = None
    db_session._sessionmaker = None


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(get_settings())
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture
async def noauth_client() -> AsyncIterator[AsyncClient]:
    """Client whose app runs in AUTH_MODE=none (auto dev admin) for CRUD tests."""
    s = get_settings().model_copy(update={"auth_mode": "none"})
    app = create_app(s)
    app.dependency_overrides[get_settings] = lambda: s
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def settings() -> Settings:
    return get_settings()
