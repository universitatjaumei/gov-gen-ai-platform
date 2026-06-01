"""WorkspaceAutosaveService — 1C.1.

Persistencia atómica del estado del workspace con concurrencia optimista:
- `expected_workspace_version` y cada `expected_block_version` se validan antes de aplicar nada.
- Las transiciones de BlockState se validan contra `_VALID_TRANSITIONS` (9R.3.2).
- Si cualquier check falla, ninguna escritura se persiste (rollback completo).

Deploy: edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.redaccion.contracts.runtime import (
    InvalidBlockTransitionError as _RuntimeInvalidTransitionError,
    _VALID_TRANSITIONS,
)
from server.app.modules.redaccion.contracts.state_update import (
    BlockUpdate,
    WorkspaceStatePatch,
    WorkspaceStatePatchResponse,
)
from server.app.modules.redaccion.database.models import (
    HubWorkspace,
    HubWorkspaceBlock,
)


# ---------------------------------------------------------------------------
# Excepciones públicas del servicio
# ---------------------------------------------------------------------------


class WorkspaceNotFoundError(Exception):
    """Workspace inexistente o no pertenece al usuario."""

    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(f"Workspace {workspace_id} not found")
        self.workspace_id = workspace_id


class ConflictError(Exception):
    """Versión optimista desactualizada (workspace y/o bloques)."""

    def __init__(
        self,
        current_workspace_version: int,
        conflicting_block_ids: list[UUID] | None = None,
    ) -> None:
        ids = list(conflicting_block_ids or [])
        super().__init__(
            f"Optimistic conflict (workspace_version={current_workspace_version}, "
            f"conflicting_block_ids={ids})"
        )
        self.current_workspace_version = current_workspace_version
        self.conflicting_block_ids = ids


class InvalidTransitionError(Exception):
    """Transición de BlockState inválida (rechazada por la state machine de 9R.3.2)."""

    def __init__(self, block_id: UUID, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Invalid block transition for {block_id}: {from_status!r} → {to_status!r}"
        )
        self.block_id = block_id
        self.from_status = from_status
        self.to_status = to_status


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceAutosaveService:
    """Aplica un patch atómico de estado al workspace + bloques.

    El llamador es responsable de:
      - Pasar una `AsyncSession` que el servicio cerrará vía commit/rollback.
      - Garantizar `user_id` autenticado (el servicio sólo comprueba ownership).
    """

    session: AsyncSession

    async def apply_patch(
        self,
        workspace_id: UUID,
        user_id: str,
        patch: WorkspaceStatePatch,
    ) -> WorkspaceStatePatchResponse:
        try:
            return await self._apply_patch(workspace_id, user_id, patch)
        except Exception:
            await self.session.rollback()
            raise

    async def _apply_patch(
        self,
        workspace_id: UUID,
        user_id: str,
        patch: WorkspaceStatePatch,
    ) -> WorkspaceStatePatchResponse:
        # 1) Lock pesimista de la fila del workspace.
        ws = await self._load_workspace_for_update(workspace_id, user_id)

        # 2) Concurrencia optimista a nivel workspace.
        if ws.version != patch.expected_workspace_version:
            raise ConflictError(current_workspace_version=ws.version)

        # 3) Cargar bloques referenciados y validar version + transition (sin escribir).
        block_records = await self._load_blocks(workspace_id, patch.block_updates)
        conflicting: list[UUID] = []
        validated: list[tuple[HubWorkspaceBlock, BlockUpdate]] = []

        for update in patch.block_updates:
            block = block_records.get(update.block_id)
            if block is None:
                conflicting.append(update.block_id)
                continue
            if block.version != update.expected_block_version:
                conflicting.append(update.block_id)
                continue
            validated.append((block, update))

        if conflicting:
            raise ConflictError(
                current_workspace_version=ws.version,
                conflicting_block_ids=conflicting,
            )

        # 4) Validar transiciones antes de cualquier mutación.
        for block, update in validated:
            if update.state is not None and update.state != block.status:
                allowed = _VALID_TRANSITIONS.get(block.status, set())
                if update.state not in allowed:
                    raise InvalidTransitionError(
                        block_id=update.block_id,
                        from_status=block.status,
                        to_status=update.state,
                    )

        # 5) Aplicar mutaciones e incrementar versiones.
        now = datetime.now(timezone.utc)
        updated_block_versions: dict[UUID, int] = {}
        for block, update in validated:
            if update.content is not None:
                block.content_json = update.content
            if update.state is not None:
                block.status = update.state
            block.version = block.version + 1
            block.updated_at = now
            updated_block_versions[update.block_id] = block.version

        ws.version = ws.version + 1
        ws.updated_at = now

        await self.session.flush()
        await self.session.commit()

        return WorkspaceStatePatchResponse(
            workspace_version=ws.version,
            updated_block_versions=updated_block_versions,
            saved_at=now,
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    async def _load_workspace_for_update(
        self, workspace_id: UUID, user_id: str
    ) -> HubWorkspace:
        stmt = (
            select(HubWorkspace)
            .where(HubWorkspace.id == workspace_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        ws = result.scalar_one_or_none()
        if ws is None or str(ws.owner_id) != str(user_id):
            # Una sola excepción para ambos casos: evita leaks de existencia.
            raise WorkspaceNotFoundError(workspace_id)
        return ws

    async def _load_blocks(
        self, workspace_id: UUID, updates: list[BlockUpdate]
    ) -> dict[UUID, HubWorkspaceBlock]:
        if not updates:
            return {}
        ids = [u.block_id for u in updates]
        stmt = select(HubWorkspaceBlock).where(
            and_(
                HubWorkspaceBlock.workspace_id == workspace_id,
                HubWorkspaceBlock.id.in_(ids),
            )
        )
        result = await self.session.execute(stmt)
        blocks = list(result.scalars().all())
        return {block.id: block for block in blocks}


# Re-export por compatibilidad con la state machine de 9R.3.2 (algunos llamadores
# capturan `InvalidBlockTransitionError`).
__all__ = [
    "WorkspaceAutosaveService",
    "WorkspaceNotFoundError",
    "ConflictError",
    "InvalidTransitionError",
    "_RuntimeInvalidTransitionError",
]
