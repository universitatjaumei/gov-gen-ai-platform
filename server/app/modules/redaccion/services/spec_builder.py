"""Del borrador propuesto a la plantilla que el sistema sabe leer (VER.3). Deploy: edge.

`approve-as-template` guardaba en `spec_json` el **borrador** tal cual —`proposed_sections`,
`proposed_blocks`, `proposed_inputs`, `rationale`—. Una `ReportTemplateSpec` es otra cosa, así
que toda plantilla aprobada desde una propuesta de IA quedaba inservible: el contrato de UI
devolvía 500 y la generación no podía leerla. Nadie lo había visto porque nadie había
recorrido el camino entero.

Lo único que no es traducción directa es el **contrato de UI**, que el borrador no trae y hay
que derivar: un slot de fichero es una zona de arrastre y uno de dato es un campo. Es lo que
hace que el formulario del asistente se construya solo, que es la regla maestra nº1 del
proyecto.
"""
from __future__ import annotations

from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
from server.app.modules.redaccion.contracts.inputs import InputContract, InputSlot
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
)
from server.app.modules.redaccion.contracts.ui import (
    ReportUIContract,
    UIDropzoneDescriptor,
    UIFieldDescriptor,
    UISection,
)

_TIPOS_IA = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})

#: Extensiones que acepta cada zona de arrastre, por tipo de slot.
_ACEPTA = {
    "pdf": [".pdf"],
    "excel": [".xlsx", ".xls"],
    "csv": [".csv"],
    "markdown": [".md", ".markdown"],
}

#: Slots que se resuelven subiendo un fichero. El resto se teclean.
#
# INF.1 — se deriva de `_ACEPTA` en vez de escribirse a mano. Iba
# `frozenset({"pdf", "excel", "csv"})` y **se quedó corta cuando SEG.3 añadió `markdown`**:
# las dos tablas discrepaban, así que un slot de markdown salía como campo de texto en vez de
# como zona de subida, y un fichero no se puede teclear. Un tipo es de fichero si y solo si
# tiene extensiones declaradas, con lo que no pueden volver a desincronizarse. Es la tercera
# vez en el módulo que una lista escrita a mano se queda corta (tipos de gráfico y operaciones
# de ETL en GUI.3, `md_table` en SEG.3), y la misma solución.
TIPOS_DE_FICHERO = frozenset(_ACEPTA)


def _todos_los_slots(inputs: InputContract) -> list[InputSlot]:
    return list(inputs.required_slots) + list(inputs.optional_slots)


def _contrato_de_ui(borrador: ReportTemplateDraft, hay_ia: bool) -> ReportUIContract:
    slots = _todos_los_slots(borrador.proposed_inputs)
    requeridos = {s.slot_id for s in borrador.proposed_inputs.required_slots}

    return ReportUIContract(
        wizard_steps=[
            UISection(id=s.id, title=s.title, order=s.order, block_ids=list(s.block_ids))
            for s in borrador.proposed_sections
        ],
        dropzones=[
            UIDropzoneDescriptor(
                slot_id=s.slot_id,
                label=s.label,
                accept=_ACEPTA.get(s.kind, []),
                multiple=s.multiple,
                max_size_mb=s.max_size_mb,
                required=s.slot_id in requeridos,
            )
            for s in slots
            if s.kind in TIPOS_DE_FICHERO
        ],
        manual_fields=[
            UIFieldDescriptor(
                slot_id=s.slot_id,
                label=s.label,
                field_type=s.kind,
                required=s.slot_id in requeridos,
            )
            for s in slots
            if s.kind not in TIPOS_DE_FICHERO
        ],
        # El editor de bloques se ofrece siempre: es la vía por la que se corrige lo
        # generado, y una plantilla sin él obliga a rehacer el informe entero por una frase.
        block_editor_enabled=True,
        ai_review_panel_enabled=hay_ia,
        preview_layout="markdown",
    )


def spec_desde_borrador(borrador: ReportTemplateDraft) -> ReportTemplateSpec:
    """La plantilla que corresponde a un borrador ya validado.

    Las políticas se deducen de lo que el borrador contiene, no se preguntan: una plantilla
    con bloques de IA los permite, y una con `REVIEW_GATE` exige revisión. Deducirlas evita
    el estado imposible —política que prohíbe la IA en una plantilla llena de bloques de IA—
    que nadie miraría hasta que fallara la generación.
    """
    tipos = {b.kind for b in borrador.proposed_blocks}
    hay_ia = bool(tipos & _TIPOS_IA)

    return ReportTemplateSpec(
        sections=list(borrador.proposed_sections),
        blocks=list(borrador.proposed_blocks),
        input_contract=borrador.proposed_inputs,
        ui_contract=_contrato_de_ui(borrador, hay_ia),
        ai_block_policy=AIBlockPolicy.ALLOWED if hay_ia else AIBlockPolicy.DISABLED,
        review_policy=(
            ReviewPolicy.REQUIRED if "REVIEW_GATE" in tipos else ReviewPolicy.NONE
        ),
        export_policy=ExportPolicy.DOCX,
    )
