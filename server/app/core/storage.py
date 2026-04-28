"""Abstracción de almacenamiento de objetos basada en fsspec.

El backend se configura por variables de entorno:
  STORAGE_BACKEND  → "file" (local), "s3" (MinIO/AWS), "gcs" (Google Cloud Storage)
  STORAGE_BUCKET   → ruta base (directorio local o nombre de bucket)
  STORAGE_ENDPOINT → URL del endpoint (solo backend "s3" con endpoint personalizado)
  STORAGE_ACCESS_KEY / STORAGE_SECRET_KEY → credenciales S3/MinIO

En producción GCP las credenciales para "gcs" se leen automáticamente vía
Application Default Credentials (ADC) o GOOGLE_APPLICATION_CREDENTIALS.
"""
from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import Protocol, runtime_checkable

import fsspec


@runtime_checkable
class StorageService(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...


class FsspecStorageService:

    def __init__(self, backend: str, bucket: str, **kwargs) -> None:
        # Normalizar separadores para compatibilidad Windows/GCS/S3
        self._bucket = bucket.replace("\\", "/").rstrip("/")
        self._fs = fsspec.filesystem(backend, **kwargs)

    def _full_path(self, key: str) -> str:
        return f"{self._bucket}/{key}"

    async def put(self, key: str, data: bytes) -> None:
        path = self._full_path(key)
        await asyncio.to_thread(self._sync_put, path, data)

    def _sync_put(self, path: str, data: bytes) -> None:
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        if parent:
            try:
                self._fs.makedirs(parent, exist_ok=True)
            except (FileExistsError, NotImplementedError):
                pass
        with self._fs.open(path, "wb") as f:
            f.write(data)

    async def get(self, key: str) -> bytes:
        if not await self.exists(key):
            raise FileNotFoundError(f"Key not found in storage: {key}")
        path = self._full_path(key)
        return await asyncio.to_thread(self._sync_get, path)

    def _sync_get(self, path: str) -> bytes:
        with self._fs.open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        await asyncio.to_thread(self._fs.rm, path)

    async def exists(self, key: str) -> bool:
        path = self._full_path(key)
        return await asyncio.to_thread(self._fs.exists, path)


@lru_cache(maxsize=1)
def _build_storage_service() -> FsspecStorageService:
    backend = os.environ.get("STORAGE_BACKEND", "file")
    bucket = os.environ.get("STORAGE_BUCKET", "/tmp/govgenai")
    kwargs: dict = {}
    if backend == "s3":
        endpoint = os.environ.get("STORAGE_ENDPOINT")
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        kwargs["key"] = os.environ.get("STORAGE_ACCESS_KEY", "")
        kwargs["secret"] = os.environ.get("STORAGE_SECRET_KEY", "")
    return FsspecStorageService(backend=backend, bucket=bucket, **kwargs)


def get_storage_service() -> FsspecStorageService:
    return _build_storage_service()
