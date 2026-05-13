"""ValidateInputContractNode — verifica que todos los slots requeridos están presentes (9R.6.1)."""
from __future__ import annotations

from server.app.modules.redaccion.contracts.runtime import ExtractionWarning, WorkspaceState


class ValidateInputContractNode:
    """Emite advertencias para cada slot requerido ausente en state.inputs."""

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        existing = set(state.inputs.keys())
        new_warnings = list(state.warnings)

        for slot in state.spec.input_contract.required_slots:
            if slot.slot_id not in existing:
                new_warnings.append(
                    ExtractionWarning(
                        block_id=None,
                        message=f"Required input slot missing: {slot.slot_id!r}",
                        kind="missing_input",
                    )
                )

        return {"warnings": new_warnings}
