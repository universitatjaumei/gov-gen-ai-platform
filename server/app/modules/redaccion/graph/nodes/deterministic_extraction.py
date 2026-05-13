"""DeterministicExtractionNode — ejecuta pipelines de extracción para bloques DETERMINISTIC_DATA (9R.6.2/9R.6.6)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from server.app.modules.redaccion.contracts.runtime import ExtractionWarning, WorkspaceState
from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef


_SLOT_KIND_TO_SOURCE: dict[str, set[str]] = {
    "excel": {"excel"},
    "pdf":   {"pdf_text", "pdf_table"},
    "text":  {"manual"},
    "csv":   {"excel"},
}


def _find_artifact_for_pipeline(source_pipeline: str, spec, artifacts_normalized: dict[str, str]) -> StorageRef | None:
    all_slots = list(spec.input_contract.required_slots) + list(spec.input_contract.optional_slots)
    for slot in all_slots:
        matched_pipelines = _SLOT_KIND_TO_SOURCE.get(slot.kind, set())
        if source_pipeline in matched_pipelines and slot.slot_id in artifacts_normalized:
            path = artifacts_normalized[slot.slot_id]
            parts = path.split("/", 1)
            bucket, key = (parts[0], parts[1]) if len(parts) == 2 else (path, "")
            return StorageRef(bucket=bucket, key=key)
    return None


class DeterministicExtractionNode:
    """Ejecuta la extracción determinista para todos los bloques DETERMINISTIC_DATA del spec.

    En caso de fallo por bloque: marca status=failed(extraction_failed) y continúa
    con el resto (el CoreGraph NO aborta).
    """

    def __init__(self, factory: Any) -> None:
        self._factory = factory

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        updated_blocks = dict(state.blocks)
        new_warnings = list(state.warnings)
        new_block_outputs = dict(state.block_outputs)
        now = datetime.now(timezone.utc)

        for block_contract in state.spec.blocks:
            if block_contract.kind != "DETERMINISTIC_DATA":
                continue

            block_id = block_contract.id
            if block_id not in updated_blocks:
                continue

            source_kind = block_contract.source_pipeline
            file_ref = _find_artifact_for_pipeline(source_kind, state.spec, state.artifacts_normalized)

            if file_ref is None and not state.artifacts_normalized:
                new_warnings.append(ExtractionWarning(
                    block_id=block_id,
                    message=f"No artifact found for block {block_id!r} (source_pipeline={source_kind!r}).",
                    kind="missing_input",
                ))
                continue

            inp = ExtractionInput(source_kind=source_kind, file_ref=file_ref, options={})

            try:
                pipeline = self._factory.get(source_kind)
                result = pipeline.extract(inp)
            except Exception as exc:
                new_warnings.append(ExtractionWarning(
                    block_id=block_id, message=str(exc), kind="extraction_error",
                ))
                updated_blocks[block_id] = updated_blocks[block_id].model_copy(update={
                    "status": "failed",
                    "failure_kind": "extraction_failed",
                    "last_error_message": str(exc)[:500],
                    "last_updated_by": "system",
                    "updated_at": now,
                })
                new_block_outputs[block_id] = {"partial": {}}
                continue

            content = {
                "tables": [t.model_dump() for t in result.tables],
                "metrics": [m.model_dump() for m in result.metrics],
                "free_text": result.free_text,
            }
            for pw in result.warnings:
                new_warnings.append(ExtractionWarning(
                    block_id=block_id, message=pw.message, kind=pw.code.lower(),
                ))

            block_state = updated_blocks[block_id]
            new_status = "extracted" if block_state.status in ("draft", "missing_input") else block_state.status
            updated_blocks[block_id] = block_state.model_copy(update={
                "content": content,
                "status": new_status,
                "last_updated_by": "system",
                "updated_at": now,
            })

        return {"blocks": updated_blocks, "warnings": new_warnings, "block_outputs": new_block_outputs}
