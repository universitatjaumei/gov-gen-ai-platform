"""AuditLogNode — cierra el grafo emitiendo DraftingRunManifest y actualizando el trace (9R.6.5/9R.6.6)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from server.app.modules.redaccion.contracts.manifest import DraftingRunManifest, FailedBlockInfo
from server.app.modules.redaccion.contracts.runtime import WorkspaceState
from server.app.modules.redaccion.database.models import HubRunManifest


class AuditLogNode:
    """Persiste el DraftingRunManifest e instrumenta el span raíz de Langfuse.

    Puede ejecutarse incluso si el workspace está en estado 'error':
    cualquier ejecución del grafo deja un manifest persistido.
    """

    def __init__(self, manifest_repo: Any, tracing_service: Any) -> None:
        self._repo = manifest_repo
        self._tracing = tracing_service

    async def __call__(self, state: WorkspaceState) -> dict:
        span = self._tracing.open_trace(
            "redaccion.run",
            workspace_id=str(state.workspace_id),
            template_version_id=str(state.template_version_id),
        )

        manifest_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Recopilar aprobaciones de los bloques
        approvals = [
            b.approval
            for b in state.blocks.values()
            if b.approval is not None
        ]

        # Recopilar bloques fallidos para trazabilidad
        failed_blocks = [
            FailedBlockInfo(
                block_id=b.block_id,
                failure_kind=b.failure_kind,
                last_error_message=b.last_error_message,
                retry_attempts=b.retry_attempts,
            )
            for b in state.blocks.values()
            if b.status == "failed" and b.failure_kind is not None
        ]

        manifest = DraftingRunManifest(
            id=manifest_id,
            workspace_id=state.workspace_id,
            template_version_id=state.template_version_id,
            report_profile=state.report_profile,
            warnings=list(state.warnings),
            user_approvals=approvals,
            failed_blocks=failed_blocks,
            final_document_hash=state.final_document_hash,
            status_at_close=state.status,
            created_at=now,
        )

        # Persistir en BD
        orm = HubRunManifest(
            id=manifest_id,
            workspace_id=state.workspace_id,
            template_version_id=state.template_version_id,
            report_profile=state.report_profile,
            payload_json=manifest.model_dump(mode="json"),
            final_document_hash=state.final_document_hash,
            created_at=now,
        )
        await self._repo.save(orm)

        span.set_attribute("run_manifest_id", str(manifest_id))
        span.end()

        return {"run_manifest_id": manifest_id}
