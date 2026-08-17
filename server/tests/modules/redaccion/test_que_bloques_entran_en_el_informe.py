"""VER.4 — qué bloques entran en el informe ensamblado.

Al recorrer el camino apareció que un informe ensamblado hoy contendría **solo los bloques de
IA que el humano aprobó**: el texto fijo, la tabla y el gráfico se descartaban en silencio.
Es decir, la mitad determinista del informe —la que el usuario describió como el motivo del
módulo— desaparecía. Y la vista previa, que exige *todos* los bloques aprobados, era
inalcanzable por construcción: nada transiciona un `STATIC_TEXT` a `approved`.

**Interpretación aplicada** (desviación documentada): la puerta de revisión es sobre el
**texto de IA**, que es lo que `UserReviewGateNode` implementa —solo transiciona bloques de
IA a `needs_review`—. Un bloque determinista no lo aprueba nadie porque no lo escribió nadie:
sale de un fichero que el usuario subió. Así que entra en el informe si tiene contenido, y
solo los de IA exigen aprobación.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from server.app.modules.redaccion.contracts.blocks import (
    AIAssistedTextBlock,
    DeterministicDataBlock,
    StaticTextBlock,
)
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
    SectionContract,
)
from server.app.modules.redaccion.contracts.ui import ReportUIContract
from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode


def _spec() -> ReportTemplateSpec:
    return ReportTemplateSpec(
        sections=[SectionContract(
            id="s1", title="Informe", order=1,
            block_ids=["b_texto", "b_datos", "b_resumen"],
        )],
        blocks=[
            StaticTextBlock(id="b_texto", title="Encabezado", order=1, content="Cabecera"),
            DeterministicDataBlock(
                id="b_datos", title="Importes", order=2, source_pipeline="excel"
            ),
            AIAssistedTextBlock(
                id="b_resumen", title="Resumen", order=3,
                ai_prompt_template_id="generic_report_v1", review_policy_id="required",
            ),
        ],
        input_contract=InputContract(),
        ui_contract=ReportUIContract(
            wizard_steps=[], dropzones=[], manual_fields=[],
            block_editor_enabled=True, ai_review_panel_enabled=True,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.ALLOWED,
        review_policy=ReviewPolicy.REQUIRED,
        export_policy=ExportPolicy.DOCX,
    )


def _bloque(block_id: str, kind: str, status: str, texto: str) -> BlockState:
    return BlockState(
        block_id=block_id, kind=kind, status=status,
        content={"text": texto},
        last_updated_by="system", updated_at=datetime.now(timezone.utc),
    )


def _estado(estado_del_resumen: str = "approved") -> WorkspaceState:
    return WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={
            "b_texto": _bloque("b_texto", "STATIC_TEXT", "draft", "Cabecera"),
            "b_datos": _bloque("b_datos", "DETERMINISTIC_DATA", "extracted", "120.000 EUR"),
            "b_resumen": _bloque("b_resumen", "AI_ASSISTED_TEXT", estado_del_resumen, "Resumen."),
        },
        status="drafting",
        warnings=[],
        spec=_spec(),
    )


class TestElInformeEnsamblado:

    @pytest.mark.asyncio
    async def test_should_include_the_deterministic_half_of_the_report(self):
        """Es la mitad que da sentido al módulo: sale de un fichero, no de un modelo."""
        salida = await FinalAssemblerNode()(_estado())

        assert "Cabecera" in salida["final_document"]
        assert "120.000 EUR" in salida["final_document"]

    @pytest.mark.asyncio
    async def test_should_include_the_ai_text_once_a_human_approved_it(self):
        salida = await FinalAssemblerNode()(_estado(estado_del_resumen="approved"))

        assert "Resumen." in salida["final_document"]

    @pytest.mark.asyncio
    async def test_should_leave_out_ai_text_nobody_approved(self):
        """Lo que el modelo escribió y nadie miró **no** sale en el informe: es la razón de
        ser de la puerta de revisión."""
        salida = await FinalAssemblerNode()(_estado(estado_del_resumen="needs_review"))

        assert "Resumen." not in salida["final_document"]
        assert "Cabecera" in salida["final_document"]


class TestLaVistaPrevia:

    def test_should_only_wait_for_the_blocks_a_human_has_to_approve(self):
        """Exigía **todos** los bloques aprobados, y nada transiciona un `STATIC_TEXT` a
        `approved`: la vista previa era inalcanzable por construcción."""
        from server.app.modules.redaccion.services.preview_builder import bloques_pendientes

        bloques = [
            _bloque("b_texto", "STATIC_TEXT", "draft", "Cabecera"),
            _bloque("b_datos", "DETERMINISTIC_DATA", "extracted", "120.000"),
            _bloque("b_resumen", "AI_ASSISTED_TEXT", "approved", "Resumen."),
        ]

        assert bloques_pendientes(bloques) == []

    def test_should_still_wait_for_ai_text_pending_review(self):
        from server.app.modules.redaccion.services.preview_builder import bloques_pendientes

        bloques = [
            _bloque("b_texto", "STATIC_TEXT", "draft", "Cabecera"),
            _bloque("b_resumen", "AI_ASSISTED_TEXT", "needs_review", "Resumen."),
        ]

        assert bloques_pendientes(bloques) == ["b_resumen"]
