"""Object storage abstraction. Local filesystem backend (dev/tests) + MinIO/S3 (canonical)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def healthy(self) -> bool: ...


class LocalFileStorage:
    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.base / key).resolve()
        if not str(p).startswith(str(self.base.resolve())):
            raise ValueError("invalid storage key")
        return p

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def healthy(self) -> bool:
        try:
            probe = self.base / ".healthz"
            probe.write_bytes(b"ok")
            probe.unlink()
            return True
        except OSError:
            return False


class MinioStorage:
    def __init__(self, settings: Settings) -> None:
        from minio import Minio

        self._bucket = settings.storage_bucket
        self._client = Minio(
            settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_secure,
        )

    def put(self, key: str, data: bytes) -> str:
        import io

        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        self._client.put_object(self._bucket, key, io.BytesIO(data), length=len(data))
        return key

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(self._bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def healthy(self) -> bool:
        try:
            self._client.bucket_exists(self._bucket)
            return True
        except Exception:  # noqa: BLE001
            return False


def get_storage(settings: Settings | None = None) -> Storage:
    settings = settings or get_settings()
    if settings.storage_backend == "minio":
        return MinioStorage(settings)
    return LocalFileStorage(settings.storage_local_dir)
