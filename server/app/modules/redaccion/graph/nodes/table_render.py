"""TableRenderNode — pinta los bloques TABLE de la plantilla (SEG.5).

Deploy: edge.

`TABLE` estaba en el contrato, el validador le exigía `data_block_ref` y el prompt lo ofrecía al
modelo, pero **ningún nodo lo rellenaba**: un informe con nueve tablas salía con las nueve
vacías, sin error y sin aviso. Es literalmente el agujero que PRO.5 tapó para los gráficos, un
tipo de bloque más tarde.

Este nodo no interpreta nada: copia al bloque las tablas del bloque de datos que referencia, tal
como salieron de la extracción o de la transformación —«No hay valor» incluido—. En un informe de
seguimiento la tabla es la parte que no puede proponer un modelo: se reproduce del dato o no se
pone. La prosa la escribe la IA después, y el humano la aprueba.

Escribir en `content` y no en la vista previa hace que lo mismo valga para la pantalla y para el
DOCX, que ya saben pintar `tables` desde PRO.3, y que quede en el registro qué se imprimió.
"""
from __future__ import annotations

from datetime import datetime, timezone

from server.app.modules.redaccion.contracts.runtime import ExtractionWarning, WorkspaceState


class TableRenderNode:
    """Rellena cada bloque TABLE con los datos del bloque que referencia."""

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        bloques = dict(state.blocks)
        avisos = list(state.warnings)
        ahora = datetime.now(timezone.utc)

        for contrato in state.spec.blocks:
            if contrato.kind != "TABLE" or contrato.id not in bloques:
                continue

            referencia = getattr(contrato, "data_block_ref", None)
            origen = bloques.get(referencia) if referencia else None
            if origen is None:
                # No se pinta «lo que haya»: una tabla equivocada en un informe institucional
                # es peor que un hueco, porque nadie la vuelve a comprobar.
                avisos.append(ExtractionWarning(
                    block_id=contrato.id,
                    message=(
                        f"El bloque «{contrato.id}» pinta los datos de «{referencia}», que no "
                        f"está en el informe."
                    ),
                    kind="missing_data",
                ))
                continue

            tablas = ((origen.content or {}).get("tables")) or []
            if not tablas:
                avisos.append(ExtractionWarning(
                    block_id=contrato.id,
                    message=(
                        f"«{referencia}» no trajo ninguna tabla, así que «{contrato.id}» se "
                        f"queda sin pintar."
                    ),
                    kind="missing_data",
                ))
                continue

            bloques[contrato.id] = bloques[contrato.id].model_copy(update={
                "content": {"tables": tablas, "source_block_id": referencia},
                "status": "extracted",
                "last_updated_by": "system",
                "updated_at": ahora,
            })

        return {"blocks": bloques, "warnings": avisos}
