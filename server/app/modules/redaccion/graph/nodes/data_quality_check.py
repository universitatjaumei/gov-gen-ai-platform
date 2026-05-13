"""DataQualityCheckNode — inspecciona warnings críticos y pausa el grafo si los hay (9R.6.2)."""
from __future__ import annotations

from server.app.modules.redaccion.contracts.runtime import WorkspaceState

_CRITICAL_KINDS = frozenset({
    "no_tables_found",
    "missing_required_columns",
    "non_extractable_pdf",
    "extraction_error",
})


class DataQualityCheckNode:
    """Detecta warnings de extracción críticos y marca el workspace como 'in_review'."""

    async def __call__(self, state: WorkspaceState) -> dict:
        has_critical = any(w.kind in _CRITICAL_KINDS for w in state.warnings)
        if has_critical:
            return {"status": "in_review"}
        return {}


def data_quality_router(state: WorkspaceState) -> str:
    """Función de enrutado para el grafo: 'ask_user' si hay errores, 'ok' si no."""
    if state.status == "in_review":
        return "ask_user"
    return "ok"
