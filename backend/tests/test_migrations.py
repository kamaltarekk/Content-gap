from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg

from tests.conftest import requires_db

BACKEND = Path(__file__).resolve().parents[1]
MIGRATE_DSN = "postgresql://cgi:cgi@localhost:5433/cdga_migrate"


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = "postgresql+asyncpg://cgi:cgi@localhost:5433/cdga_migrate"
    return subprocess.run(
        ["python", "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )


def _users_exists() -> bool:
    with psycopg.connect(MIGRATE_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.users')")
        return cur.fetchone()[0] is not None


@requires_db
def test_migration_upgrade_and_downgrade() -> None:
    # Start clean.
    down = _alembic("downgrade", "base")
    assert down.returncode == 0, down.stderr

    up = _alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr
    assert _users_exists(), "users table missing after upgrade"

    back = _alembic("downgrade", "base")
    assert back.returncode == 0, back.stderr
    assert not _users_exists(), "users table should be gone after downgrade"

    # Leave the migrate DB at head for a realistic state.
    assert _alembic("upgrade", "head").returncode == 0
