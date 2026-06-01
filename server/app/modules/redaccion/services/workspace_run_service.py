"""WorkspaceRunService — orquesta el DraftingCoreGraph para un workspace (9R.10.2).

Deploy: edge

Punto de entrada único desde los endpoints HTTP al pipeline completo.
Mantiene las dependencias del grafo (storage, llm, factories, repos) inyectables
para que el mismo servicio pueda usarse en producción y en tests.

run_sync(dry_run=True) genera un resultado sintético sin tocar BD ni LLM;
existe para que el endpoint POST /run pueda devolver una respuesta inmediata
y para que los tests del slice MVP puedan verificar el contrato sin levantar
todo el stack.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from server.app.modules.redaccion.contracts.manifest import (
    AIBlockSummary,
    DraftingRunManifest,
    ExtractedBlockSummary,
    InputContractValidationResult,
)


class InputsNotReadyError(Exception):
    """Raised cuando faltan slots requeridos para arrancar el grafo."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(
            f"Workspace inputs are missing required slots: {missing}"
        )
        self.missing = missing


@dataclass
class BlockRunSummary:
    block_id: str
    kind: str
    status: str
    content: dict | None = None


@dataclass
class WorkspaceRunResult:
    run_id: UUID
    workspace_id: UUID
    status: str  # queued | running | completed | error
    blocks: list[BlockRunSummary] = field(default_factory=list)
    extraction_completed: bool = False
    extraction_completed_at: datetime | None = None
    ai_drafting_started: bool = False
    ai_drafting_started_at: datetime | None = None
    manifest_id: UUID | None = None
    manifest: DraftingRunManifest | None = None


class WorkspaceRunService:
    """Punto de wire-up del slice MVP.

    Todas las dependencias son opcionales para que el servicio sea instanciable
    sin contexto (útil para dry_run y para validaciones puramente in-memory).
    """

    def __init__(
        self,
        session: Any = None,
        storage_service: Any = None,
        llm_service: Any = None,
        extraction_factory: Any = None,
        etl_llm: Any = None,
        etl_model_name: str = "",
        tracing_service: Any = None,
    ) -> None:
        self._session = session
        self._storage = storage_service
        self._llm = llm_service
        self._extraction_factory = extraction_factory
        self._etl_llm = etl_llm
        self._etl_model_name = etl_model_name
        self._tracing = tracing_service

    # ------------------------------------------------------------------
    # Validación de inputs
    # ------------------------------------------------------------------
    def validate_inputs(self, workspace_id: UUID, uploaded_slots: list[str]) -> None:
        """Lanza InputsNotReadyError si no hay slots subidos.

        En implementaciones futuras este check cruzará uploaded_slots contra
        InputContract.required_slots de la spec asociada al workspace. Para el
        MVP, basta con detectar que no se ha subido nada.
        """
        if not uploaded_slots:
            raise InputsNotReadyError(missing=["<all_required>"])

    # ------------------------------------------------------------------
    # Modo dry-run (sin BD, sin LLM, sin grafo real)
    # ------------------------------------------------------------------
    def run_sync(self, workspace_id: UUID, dry_run: bool = False) -> WorkspaceRunResult:
        """Construye un WorkspaceRunResult sintético.

        Útil para tests del contrato del slice y para devolver una respuesta
        determinista al endpoint POST /run mientras la ejecución asíncrona del
        grafo se enchufa en una fase posterior.
        """
        if not dry_run:
            raise RuntimeError(
                "run_sync(dry_run=False) no está implementado. "
                "Usa start_run() (async) para ejecuciones reales."
            )

        now = datetime.now(timezone.utc)
        extraction_at = now
        ai_at = now + timedelta(milliseconds=1)

        ai_block = BlockRunSummary(
            block_id="b_ai_synthetic",
            kind="AI_ASSISTED_TEXT",
            status="needs_review",
            content={"text": "Synthetic AI content (dry-run)."},
        )
        det_block = BlockRunSummary(
            block_id="b_det_synthetic",
            kind="DETERMINISTIC_DATA",
            status="extracted",
            content={"value": 0},
        )

        manifest_id = uuid.uuid4()
        manifest = DraftingRunManifest(
            id=manifest_id,
            workspace_id=workspace_id,
            template_version_id=uuid.uuid4(),
            report_profile="GENERIC_REPORT",
            input_contract_validation=InputContractValidationResult(valid=True),
            extracted_blocks=[
                ExtractedBlockSummary(
                    block_id="b_det_synthetic",
                    kind="DETERMINISTIC_DATA",
                    status="extracted",
                )
            ],
            ai_blocks=[
                AIBlockSummary(
                    block_id="b_ai_synthetic",
                    kind="AI_ASSISTED_TEXT",
                    status="needs_review",
                )
            ],
            final_document_hash=f"sha256:dryrun-{manifest_id.hex[:16]}",
            status_at_close="assembled",
            created_at=now,
        )

        return WorkspaceRunResult(
            run_id=uuid.uuid4(),
            workspace_id=workspace_id,
            status="completed",
            blocks=[det_block, ai_block],
            extraction_completed=True,
            extraction_completed_at=extraction_at,
            ai_drafting_started=True,
            ai_drafting_started_at=ai_at,
            manifest_id=manifest_id,
            manifest=manifest,
        )

    # ------------------------------------------------------------------
    # Encolado de ejecución real (semántica queue-and-poll)
    # ------------------------------------------------------------------
    async def start_run(
        self,
        workspace_id: UUID,
        *,
        validate: bool = False,
    ) -> WorkspaceRunResult:
        """Marca el workspace como 'drafting' y devuelve un run_id.

        Para el MVP no dispara la ejecución del grafo en background — eso queda
        para un follow-up con Celery / asyncio.create_task. Lo que sí hace:

        - Carga el workspace
        - (opcional) valida que existen inputs subidos
        - Transiciona status: draft|ingesting → drafting
        - Devuelve `{run_id, status: 'queued'}`
        """
        from server.app.modules.redaccion.database.repos import WorkspaceRepo

        repo = WorkspaceRepo(self._session) if self._session is not None else None
        if repo is not None:
            workspace = await repo.get(workspace_id)
            if workspace is None:
                raise LookupError(f"Workspace {workspace_id} not found")

            if validate:
                inputs_json = workspace.inputs_json
                uploaded_slots = (
                    list(inputs_json.keys()) if isinstance(inputs_json, dict) else []
                )
                self.validate_inputs(workspace_id, uploaded_slots)

            if workspace.status in ("draft", "ingesting"):
                workspace.status = "drafting"

            await self._session.commit()

        return WorkspaceRunResult(
            run_id=uuid.uuid4(),
            workspace_id=workspace_id,
            status="queued",
        )
