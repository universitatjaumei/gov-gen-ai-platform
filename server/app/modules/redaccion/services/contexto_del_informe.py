"""Lo que el copiloto necesita saber del informe abierto (INF.10).

Deploy: edge

En las pruebas del 2026-08-20 el usuario le preguntó «no sé dónde aprobar los bloques» y no
obtuvo respuesta. La razón: el copiloto responde con RAG **sobre la documentación del proyecto**
y no sabe nada del informe que hay delante — ni qué apartados tiene, ni en qué estado están, ni
qué falta.

El legacy sí lo tenía. `client_app/app/core/state.py:79` dejaba anotado el motivo: los datos
cargados se publican al estado «para que el Copiloto conozca las columnas disponibles».

**Dos reglas de forma.** La primera: se manda el **estado**, no el contenido. Los textos que
escribió la IA no hacen falta para responder «dónde apruebo esto», y no mandarlos es la
diferencia entre un contexto de doscientas palabras y uno de veinte mil. La segunda: lo poco
que puede llevar datos —el texto de los avisos— **se anonimiza**, porque el modelo puede estar
en la nube; es la misma frontera que aplica INF.4 a la muestra de datos.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from server.app.modules.redaccion.services.block_actions import (
    acciones_permitidas,
    bloques_pendientes,
)


async def contexto_del_informe(
    workspace_repo: Any,
    block_repo: Any,
    template_version_repo: Any,
    workspace_id: UUID,
) -> str | None:
    """El estado del informe en texto, listo para el prompt. `None` si no hay informe.

    Se compone con los repos y no con una sesión suelta para que se pueda probar con dobles,
    igual que `PreviewBuilderService`.
    """
    workspace = await workspace_repo.get(workspace_id)
    if workspace is None:
        return None

    bloques = await block_repo.list(workspace_id)
    subidos = set((workspace.inputs_json or {}).keys())

    lineas = [f"ESTADO DEL INFORME ABIERTO (id {workspace_id}):", f"- Estado general: {workspace.status}"]

    faltan = await _slots_que_faltan(template_version_repo, workspace, subidos)
    if faltan:
        lineas.append(
            "- Datos de partida que faltan por aportar: " + ", ".join(sorted(faltan))
        )
    elif subidos:
        lineas.append("- Datos de partida: aportados (" + ", ".join(sorted(subidos)) + ")")

    lineas.append("- Apartados:")
    for bloque in bloques:
        acciones = acciones_permitidas(kind=bloque.kind, status=bloque.status)
        cola = f" · acciones disponibles: {', '.join(acciones)}" if acciones else ""
        lineas.append(f"  · {bloque.block_id} ({bloque.kind}): {bloque.status}{cola}")

    pendientes = bloques_pendientes(list(bloques))
    if pendientes:
        lineas.append(
            "- PENDIENTE DE UNA PERSONA: hay que revisar y aprobar "
            + ", ".join(pendientes)
            + " en el panel de revisión de la propia pantalla del informe. Hasta entonces el"
            " informe no se puede ver en vista previa ni exportar."
        )
    else:
        lineas.append("- No queda nada pendiente de revisión.")

    avisos = _avisos(workspace)
    if avisos:
        lineas.append("- Avisos abiertos: " + "; ".join(avisos))

    return "\n".join(lineas)


async def _slots_que_faltan(template_version_repo: Any, workspace: Any, subidos: set[str]) -> set[str]:
    """Los slots obligatorios sin fichero. Mismo criterio que la guarda de INF.1."""
    version = await template_version_repo.get(workspace.template_version_id)
    spec = getattr(version, "spec_json", None)
    contrato = spec.get("input_contract") if isinstance(spec, dict) else None
    if not isinstance(contrato, dict):
        return set()
    requeridos = {
        slot["slot_id"]
        for slot in contrato.get("required_slots") or []
        if isinstance(slot, dict) and slot.get("slot_id")
    }
    return requeridos - subidos


def _avisos(workspace: Any) -> list[str]:
    """Los avisos del informe, **anonimizados**: los escribe el grafo sobre datos del cliente."""
    from server.app.modules.redaccion.services.anonymization.anonymizer import (
        AnonymizationContext,
    )

    brutos = workspace.warnings_json or []
    if not isinstance(brutos, list):
        return []

    contexto = AnonymizationContext()
    mensajes = [
        str(aviso.get("message", "")) if isinstance(aviso, dict) else str(aviso)
        for aviso in brutos
    ]
    return [contexto.anonymize(m) for m in mensajes if m][:8]
