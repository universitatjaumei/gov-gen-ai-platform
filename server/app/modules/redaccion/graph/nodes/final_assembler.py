"""FinalAssemblerNode — ensambla el documento Markdown final y calcula su hash (9R.6.4/9R.6.6)."""
from __future__ import annotations

import hashlib

from server.app.modules.redaccion.contracts.runtime import (
    WorkspaceBlockedByFailedBlocksError,
    WorkspaceState,
)

_INCLUDABLE_STATUSES = frozenset({"approved", "locked"})

#: Los bloques cuyo texto lo escribió un modelo. Son los únicos que exigen que un humano los
#: apruebe antes de salir en el informe.
_TIPOS_DE_IA = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})


def _entra_en_el_informe(kind: str, status: str, tiene_contenido: bool) -> bool:
    """Si este bloque debe aparecer en el documento ensamblado.

    Antes se exigía `approved`/`locked` a **todos**, y como nada transiciona un `STATIC_TEXT`
    o un `DETERMINISTIC_DATA` a `approved`, el informe salía con la mitad de IA y sin la mitad
    determinista —que es justamente la que sale de los ficheros que subió el usuario—.

    La puerta de revisión es sobre el **texto de IA**: es lo que `UserReviewGateNode`
    implementa, y lo que tiene sentido revisar. Un bloque determinista no lo aprueba nadie
    porque no lo escribió nadie.
    """
    if kind in _TIPOS_DE_IA:
        return status in _INCLUDABLE_STATUSES
    return status not in ("failed",) and tiene_contenido


def contenido_a_markdown(content: dict | None) -> str:
    """El Markdown de un bloque para el documento final.

    PRO.3 — aquí había `content.get("text") or str(content)`, así que un bloque de datos
    volcaba el **diccionario de Python** en el informe: `{'tables': [{'name': …`. Las tablas
    van como tabla de Markdown y las métricas como lista, que es lo que la exportación
    convierte en tabla y en viñetas.
    """
    if not content:
        return ""

    texto = content.get("text") or content.get("value")
    if texto:
        return str(texto)

    partes: list[str] = []

    for tabla in content.get("tables") or []:
        partes.append(_tabla_a_markdown(tabla))

    for metrica in content.get("metrics") or []:
        unidad = f" {metrica['unit']}" if metrica.get("unit") else ""
        partes.append(f"- **{metrica.get('name', '')}**: {metrica.get('value', '')}{unidad}")

    if content.get("free_text"):
        partes.append(str(content["free_text"]))

    return "\n\n".join(p for p in partes if p)


def _tabla_a_markdown(tabla: dict) -> str:
    cabeceras = [str(c) for c in (tabla.get("headers") or [])]
    filas = tabla.get("rows") or []
    if not cabeceras and not filas:
        return ""

    lineas: list[str] = []
    if tabla.get("name"):
        lineas.append(f"**{tabla['name']}**\n")
    if cabeceras:
        lineas.append("| " + " | ".join(cabeceras) + " |")
        lineas.append("|" + "|".join(" --- " for _ in cabeceras) + "|")
    for fila in filas:
        lineas.append("| " + " | ".join(str(v) for v in fila) + " |")
    return "\n".join(lineas)


class FinalAssemblerNode:
    """Renderiza el Markdown ensamblado solo con bloques en estado approved/locked.

    Respeta el orden de secciones y bloques definido en el spec.
    Calcula final_document_hash (SHA-256).
    Transición workspace: * → assembled.

    Lanza WorkspaceBlockedByFailedBlocksError si algún bloque requerido tiene status=failed
    y no está en skip_blocks.
    """

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        # Verificar bloques requeridos fallidos que no estén en skip_blocks
        failed_required = [
            b.id
            for b in state.spec.blocks
            if b.required
            and b.id not in state.skip_blocks
            and state.blocks.get(b.id) is not None
            and state.blocks[b.id].status == "failed"
        ]
        if failed_required:
            raise WorkspaceBlockedByFailedBlocksError(failed_required)

        block_index = {b.id: b for b in state.spec.blocks}
        parts: list[str] = []

        for section in sorted(state.spec.sections, key=lambda s: s.order):
            section_parts: list[str] = []

            ordered_blocks = sorted(
                (block_index[bid] for bid in section.block_ids if bid in block_index),
                key=lambda b: b.order,
            )

            for block_contract in ordered_blocks:
                block_state = state.blocks.get(block_contract.id)
                if block_state is None:
                    continue
                if not _entra_en_el_informe(
                    block_state.kind, block_state.status, bool(block_state.content)
                ):
                    continue

                texto = contenido_a_markdown(block_state.content)

                section_parts.append(f"### {block_contract.title}\n\n{texto}")

            if section_parts:
                parts.append(f"## {section.title}\n\n" + "\n\n".join(section_parts))

        document = "\n\n".join(parts)
        doc_hash = hashlib.sha256(document.encode()).hexdigest()

        return {
            "final_document": document,
            "final_document_hash": doc_hash,
            "status": "assembled",
        }
