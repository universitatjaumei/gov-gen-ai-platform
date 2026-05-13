"""FileNormalizationNode — normaliza artefactos de entrada a rutas de storage (9R.6.1)."""
from __future__ import annotations

from typing import Protocol

from server.app.modules.redaccion.contracts.runtime import WorkspaceState


class _StorageService(Protocol):
    async def get(self, key: str) -> bytes: ...


class FileNormalizationNode:
    """Puebla artifacts_normalized mapeando slot_id → storage_path validado.

    Por ahora copia el storage_path del InputArtifact directamente; en el futuro
    puede incluir conversiones de formato (p. ej. xlsx → csv).
    """

    def __init__(self, storage_service: _StorageService) -> None:
        self._storage = storage_service

    async def __call__(self, state: WorkspaceState) -> dict:
        normalized: dict[str, str] = {}
        for slot_id, artifact in state.inputs.items():
            normalized[slot_id] = artifact.storage_path
        return {"artifacts_normalized": normalized}
