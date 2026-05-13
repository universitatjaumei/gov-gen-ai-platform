"""MissingDataQuestionNode — genera preguntas HITL accionables para datos faltantes (9R.6.2)."""
from __future__ import annotations

from server.app.modules.redaccion.contracts.runtime import ExtractionWarning, WorkspaceState

_KIND_TEMPLATES: dict[str, str] = {
    "no_tables_found": "No se encontraron tablas en '{slot}'. ¿Puedes subir una versión con tablas estructuradas?",
    "missing_required_columns": "Faltan columnas requeridas en '{slot}'. {detail} ¿Puedes subir una versión corregida?",
    "non_extractable_pdf": "El PDF '{slot}' no tiene capa de texto extraíble. ¿Puedes subir una versión digital (no escaneada)?",
    "extraction_error": "Error al procesar '{slot}': {detail} ¿Puedes verificar el fichero e intentarlo de nuevo?",
    "missing_input": "Falta el fichero requerido para '{slot}'. Por favor, adjunta el documento.",
}


class MissingDataQuestionNode:
    """Transforma warnings críticos en preguntas accionables para el usuario (HITL)."""

    async def __call__(self, state: WorkspaceState) -> dict:
        new_warnings = list(state.warnings)

        for w in list(state.warnings):
            template = _KIND_TEMPLATES.get(w.kind)
            if template is None:
                continue
            slot = w.block_id or "desconocido"
            question = template.format(slot=slot, detail=w.message)
            new_warnings.append(ExtractionWarning(
                block_id=w.block_id,
                message=question,
                kind="hitl_question",
            ))

        return {"warnings": new_warnings, "status": "in_review"}
