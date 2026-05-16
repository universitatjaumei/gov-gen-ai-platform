"""DataTransformationNode — aplica bloques DATA_TRANSFORM en orden topológico (9R.5.8).

Se ejecuta entre DeterministicExtractionNode y DataQualityCheckNode.
Itera sobre los bloques DATA_TRANSFORM del spec, resuelve el DataFrame
de origen desde state.blocks/block_outputs, y aplica las operaciones
via ETLService.

Estado de bloque resultante:
  - mode=deterministic: status draft → extracted (las ops son reproducibles)
  - mode=ai:            status draft → extracted (la IA solo elige ops, no las ejecuta)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from server.app.modules.redaccion.contracts.runtime import ExtractionWarning, WorkspaceState
from server.app.modules.redaccion.services.transformation.etl_service import (
    ETLService,
    ETLServiceResult,
)


class DataTransformationNode:
    """Nodo del DraftingCoreGraph que procesa bloques DATA_TRANSFORM."""

    def __init__(self, llm_service: Any = None, model_name: str = "") -> None:
        self._llm = llm_service
        self._model_name = model_name

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        updated_blocks = dict(state.blocks)
        new_block_outputs = dict(state.block_outputs)
        new_warnings = list(state.warnings)
        now = datetime.now(timezone.utc)

        for block_contract in state.spec.blocks:
            if block_contract.kind != "DATA_TRANSFORM":
                continue

            block_id = block_contract.id
            if block_id not in updated_blocks:
                continue

            cfg = block_contract.config
            source_id = cfg.source_block_ref.block_id
            source_df = self._resolve_df(source_id, updated_blocks, new_block_outputs)

            def _resolver(bid: str) -> pd.DataFrame:
                return self._resolve_df(bid, updated_blocks, new_block_outputs)

            svc = ETLService(llm=self._llm, model_name=self._model_name)
            try:
                if cfg.mode == "deterministic":
                    result: ETLServiceResult = await svc.run(
                        df=source_df,
                        mode="deterministic",
                        operations=list(cfg.operations or []),
                        joinable_resolver=_resolver,
                    )
                else:
                    result = await svc.run(
                        df=source_df,
                        mode="ai",
                        nl_instruction=cfg.nl_instruction,
                        joinable_resolver=_resolver,
                    )
            except Exception as exc:
                new_warnings.append(
                    ExtractionWarning(
                        block_id=block_id,
                        message=str(exc),
                        kind="extraction_error",
                    )
                )
                updated_blocks[block_id] = updated_blocks[block_id].model_copy(update={
                    "status": "failed",
                    "failure_kind": "script_failed",
                    "last_error_message": str(exc)[:500],
                    "last_updated_by": "system",
                    "updated_at": now,
                })
                continue

            rows = result.dataframe.to_dict(orient="records")
            content = {
                "rows": rows,
                "operations_applied": [op.model_dump() for op in result.operations_applied],
                "model_used": result.model_used,
                "mode": cfg.mode,
            }
            new_block_outputs[block_id] = content
            updated_blocks[block_id] = updated_blocks[block_id].model_copy(update={
                "content": content,
                "status": "extracted",
                "last_updated_by": "system",
                "updated_at": now,
            })

        return {
            "blocks": updated_blocks,
            "block_outputs": new_block_outputs,
            "warnings": new_warnings,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_df(
        block_id: str,
        blocks: dict,
        block_outputs: dict,
    ) -> pd.DataFrame:
        block_state = blocks.get(block_id)
        if block_state and block_state.content:
            rows = block_state.content.get("rows")
            if isinstance(rows, list) and rows:
                return pd.DataFrame(rows)
        output = block_outputs.get(block_id) or {}
        rows = output.get("rows") if isinstance(output, dict) else None
        if isinstance(rows, list) and rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()
