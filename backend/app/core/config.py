"""Application settings. Validated on startup. Secrets never logged.

Test runs force offline behavior: the test settings set ``AI_PROVIDER=fake`` and a fake API key,
and no code path in the foundation calls the AI provider (spec §6.22, §6.23).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"

    # Auth: "session" (HttpOnly cookie) in production; "none" for local no-auth development.
    auth_mode: Literal["session", "none"] = "none"
    session_secret: str = "dev-insecure-change-me"
    session_cookie_name: str = "cdga_session"
    session_https_only: bool = False

    # Database — async URL for the app; a sync URL is derived for Alembic.
    database_url: str = "postgresql+asyncpg://cgi:cgi@localhost:5433/cdga"

    # Redis + job dispatch. "celery" = real broker; "inline" = run in-process (local dev,
    # no broker); "deferred" = record only (tests drive execute_job directly).
    redis_url: str = "redis://localhost:6379/0"
    job_dispatch: Literal["celery", "inline", "deferred"] = "inline"

    # Object storage. "local" writes to STORAGE_LOCAL_DIR (dev/test); "minio" uses S3/MinIO.
    storage_backend: str = "local"
    storage_local_dir: str = "./storage-data"
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "cdga"
    storage_secure: bool = False

    # Upload limits (spec §3.3). Configurable.
    max_file_bytes: int = 25 * 1024 * 1024
    max_manual_text_chars: int = 10_000

    # AI provider — configured, validated, but never called in the foundation phase.
    ai_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @property
    def alembic_url(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg")

    def validate_startup(self) -> None:
        if not self.anthropic_model:
            raise RuntimeError("ANTHROPIC_MODEL must be configured")
        if self.environment == "production":
            if self.auth_mode != "session":
                raise RuntimeError("Production requires AUTH_MODE=session")
            if self.session_secret in ("", "dev-insecure-change-me"):
                raise RuntimeError("Production requires a strong SESSION_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
