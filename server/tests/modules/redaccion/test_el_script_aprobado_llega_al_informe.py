"""PRO.3 — un script aprobado tiene que extraer datos dentro de un informe.

La cola de aprobación acaba incrustando el script en una plantilla, y ahí se cortaba el
camino por cuatro sitios a la vez, ninguno de ellos visible desde la cola:

1. **El bloque que escribía `approve` no tenía la forma que lee el contrato**: ponía `label`
   donde `BlockContract` espera `title`, `source_kind` donde espera `source_pipeline`, y un
   `options` que el contrato no declaraba. Una plantilla con un script aprobado no validaba.
2. **El nodo de extracción no pasaba las opciones**: construía `ExtractionInput(..., options={})`,
   así que el código del script no llegaba nunca al pipeline y éste respondía
   `SCRIPT_NOT_APPROVED`.
3. **El nodo llamaba `pipeline.extract`**, que `AdminScriptExtractionPipeline` no tiene: sólo
   `extract_async`. El bloque quedaba en `failed` con un `AttributeError` por mensaje.
4. **El artefacto no se le asignaba**: el mapa de tipos de slot a pipelines no conocía
   `admin_script`, así que el bloque no encontraba fichero que leer.

Es el mismo patrón que VER.3 y VER.4 destaparon: cada pieza probada por su lado y la costura
entre ellas sin recorrer nunca.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_CODIGO = (
    "import pandas as pd\n"
    "df = pd.read_excel(file_path)\n"
    "result = {'tables': [], 'metrics': [{'name': 'filas', 'value': len(df)}],"
    " 'free_text': None}\n"
)


# ---------------------------------------------------------------------------
# 1. La forma del bloque que se incrusta
# ---------------------------------------------------------------------------

class TestFormaDelBloqueIncrustado:
    def test_should_validar_contra_el_contrato_el_bloque_que_escribe_approve(self) -> None:
        from server.app.modules.redaccion.contracts.blocks import DeterministicDataBlock
        from server.app.routers.redaccion.scripts_router import _embed_script_block

        spec = _embed_script_block(
            {"sections": [{"id": "s1", "title": "Principal", "block_ids": []}], "blocks": {}},
            _CODIGO,
            "b-script",
        )

        bloques = spec["blocks"]
        bruto = bloques["b-script"] if isinstance(bloques, dict) else bloques[0]
        bloque = DeterministicDataBlock.model_validate(bruto)

        assert bloque.source_pipeline == "admin_script"
        assert bloque.options["code"] == _CODIGO
        assert bloque.title

    def test_should_dejar_la_plantilla_legible_por_el_grafo(self) -> None:
        """La prueba que faltaba: lo guardado se tiene que poder cargar como spec."""
        from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
        from server.app.routers.redaccion.scripts_router import _embed_script_block

        base = _spec_base().model_dump(mode="json")
        spec = ReportTemplateSpec.model_validate(_embed_script_block(base, _CODIGO, "b-script"))

        bloque = next(b for b in spec.blocks if b.id == "b-script")
        assert bloque.kind == "DETERMINISTIC_DATA"
        assert bloque.source_pipeline == "admin_script"


class TestPlantillaVaciaAlAprobar:
    """Aprobar sobre una plantilla sin spec dejaba la plantilla inservible.

    El constructor de plantillas guarda `spec_json: {}` (lo anotó VER.3), así que incrustar el
    script en su versión actual producía un spec **sin secciones, sin contrato de entrada, sin
    contrato de UI y sin políticas**. Nadie se enteraba al aprobar: el fallo salía después, con
    un 500 al pedir el contrato de UI de esa versión, y el informe no se podía ni empezar.

    Y sin contrato de entrada el script **no tendría fichero que leer**, porque el artefacto se
    busca por los slots que declara la plantilla.
    """

    def test_should_completar_un_spec_valido_sobre_una_plantilla_vacia(self) -> None:
        from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
        from server.app.routers.redaccion.scripts_router import _embed_script_block

        spec = ReportTemplateSpec.model_validate(
            _embed_script_block({}, _CODIGO, "b-script", test_data_kind="xlsx")
        )

        bloque = next(b for b in spec.blocks if b.id == "b-script")
        assert bloque.source_pipeline == "admin_script"
        # Una sección que lo contenga: si no, el bloque no entra en el informe.
        assert any("b-script" in s.block_ids for s in spec.sections)
        # Y un slot de entrada, o el script no recibe fichero.
        slots = list(spec.input_contract.required_slots) + list(spec.input_contract.optional_slots)
        assert slots, "sin slot declarado el script no tendría fichero que leer"
        assert spec.ui_contract.dropzones, "y la pantalla no tendría dónde subirlo"

    def test_should_pedir_el_tipo_de_fichero_con_el_que_se_probo(self) -> None:
        """El script se probó contra un fichero concreto: es el que hay que pedir."""
        from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
        from server.app.routers.redaccion.scripts_router import _embed_script_block

        for kind, esperado in (("xlsx", "excel"), ("csv", "csv"), ("pdf_text", "pdf")):
            spec = ReportTemplateSpec.model_validate(
                _embed_script_block({}, _CODIGO, "b-script", test_data_kind=kind)
            )
            slots = list(spec.input_contract.required_slots)
            assert slots[0].kind == esperado, kind

    def test_should_conservar_lo_que_la_plantilla_ya_tenia(self) -> None:
        """Sobre una plantilla con spec, el script se añade sin tocar lo demás."""
        from server.app.modules.redaccion.contracts.blocks import StaticTextBlock
        from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
        from server.app.routers.redaccion.scripts_router import _embed_script_block

        base = _spec_base(
            bloques=[StaticTextBlock(id="b-intro", title="Intro", content="Hola")]
        ).model_dump(mode="json")

        spec = ReportTemplateSpec.model_validate(
            _embed_script_block(base, _CODIGO, "b-script", test_data_kind="xlsx")
        )

        ids = {b.id for b in spec.blocks}
        assert ids == {"b-intro", "b-script"}
        slots = list(spec.input_contract.required_slots)
        assert [s.slot_id for s in slots] == ["datos"], (
            "el contrato de entrada que ya existía no se sustituye"
        )


# ---------------------------------------------------------------------------
# 2, 3 y 4. El nodo de extracción
# ---------------------------------------------------------------------------

def _spec_base(bloques=None, slot_kind: str = "excel"):
    """Un spec mínimo válido. Los campos obligatorios son los que exige el contrato real."""
    from server.app.modules.redaccion.contracts.inputs import InputContract, InputSlot
    from server.app.modules.redaccion.contracts.template import (
        AIBlockPolicy,
        ExportPolicy,
        ReportTemplateSpec,
        ReviewPolicy,
    )
    from server.app.modules.redaccion.contracts.ui import ReportUIContract

    return ReportTemplateSpec(
        sections=[],
        blocks=bloques or [],
        input_contract=InputContract(
            required_slots=[
                InputSlot(slot_id="datos", kind=slot_kind, label={"es": "Datos"}),
            ],
        ),
        ui_contract=ReportUIContract(
            wizard_steps=[], dropzones=[], manual_fields=[],
            block_editor_enabled=False, ai_review_panel_enabled=False,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.ALLOWED,
        review_policy=ReviewPolicy.NONE,
        export_policy=ExportPolicy.DOCX,
    )


def _spec_con_script(slot_kind: str = "excel", con_codigo: bool = True):
    from server.app.modules.redaccion.contracts.blocks import DeterministicDataBlock

    bloque = DeterministicDataBlock(
        id="b-script",
        title="Datos del script",
        source_pipeline="admin_script",
        options={"code": _CODIGO, "approved": True} if con_codigo else {},
    )
    return _spec_base(bloques=[bloque], slot_kind=slot_kind)


def _estado(spec, ruta: str):
    import uuid
    from datetime import datetime, timezone

    from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState

    return WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        spec=spec,
        blocks={
            "b-script": BlockState(
                block_id="b-script",
                kind="DETERMINISTIC_DATA",
                status="missing_input",
                last_updated_by="system",
                updated_at=datetime.now(timezone.utc),
            )
        },
        status="extracting",
        inputs={},
        warnings=[],
        artifacts_normalized={"datos": ruta},
    )


class _FactoriaDeUno:
    def __init__(self, pipeline) -> None:
        self._pipeline = pipeline

    def get(self, source_kind: str):
        assert self._pipeline.supports(source_kind), source_kind
        return self._pipeline


@pytest.mark.asyncio
async def test_should_ejecutar_el_script_aprobado_del_bloque(tmp_path: Path) -> None:
    """De punta a punta con el sandbox local: el bloque acaba `extracted` con su métrica."""
    import pandas as pd

    from server.app.core.sandbox_client import LocalSandboxClient
    from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
        DeterministicExtractionNode,
    )
    from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
        AdminScriptExtractionPipeline,
    )

    fichero = tmp_path / "datos.xlsx"
    pd.DataFrame({"a": [1, 2, 3]}).to_excel(fichero, index=False)

    nodo = DeterministicExtractionNode(
        _FactoriaDeUno(AdminScriptExtractionPipeline(client=LocalSandboxClient()))
    )

    salida = await nodo(_estado(_spec_con_script(), str(fichero)))

    bloque = salida["blocks"]["b-script"]
    assert bloque.status == "extracted", (
        f"{bloque.failure_kind}: {bloque.last_error_message} | {salida['warnings']}"
    )
    assert bloque.content["metrics"][0]["value"] == 3


@pytest.mark.asyncio
async def test_should_pasar_las_opciones_del_bloque_al_pipeline(tmp_path: Path) -> None:
    """Sin las opciones, el pipeline responde SCRIPT_NOT_APPROVED y nadie sabe por qué."""
    from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
        DeterministicExtractionNode,
    )
    from server.app.modules.redaccion.pipelines.contracts import (
        ExtractionProvenance,
        ExtractionResult,
    )
    from datetime import datetime, timezone

    recibido: dict = {}

    class _Espia:
        pipeline_id = "admin_script_pipeline_v1"

        def supports(self, source_kind: str) -> bool:
            return source_kind == "admin_script"

        async def extract_async(self, inp):
            recibido["options"] = inp.options
            recibido["file_ref"] = inp.file_ref
            return ExtractionResult(provenance=ExtractionProvenance(
                pipeline_id=self.pipeline_id,
                source_ref="espia",
                extracted_at=datetime.now(timezone.utc),
            ))

    fichero = tmp_path / "datos.xlsx"
    fichero.write_bytes(b"x")

    await DeterministicExtractionNode(_FactoriaDeUno(_Espia()))(
        _estado(_spec_con_script(), str(fichero))
    )

    assert recibido["options"]["code"] == _CODIGO
    assert recibido["options"]["approved"] is True
    assert recibido["file_ref"].key == str(fichero)


@pytest.mark.asyncio
async def test_should_asignar_el_artefacto_sea_del_tipo_que_sea(tmp_path: Path) -> None:
    """Un script lee lo que se le dé: el mapa de tipos de slot no puede excluirlo.

    Los demás pipelines sirven a un tipo concreto —`excel` para hojas de cálculo, `pdf_text`
    para PDF—, pero un script de extracción es genérico por definición: el fichero que la
    plataforma le pase es el que tiene que leer.
    """
    from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
        _find_artifact_for_pipeline,
    )

    for kind in ("excel", "pdf", "csv", "text"):
        spec = _spec_con_script(slot_kind=kind)
        ref = _find_artifact_for_pipeline("admin_script", spec, {"datos": "/tmp/x"})
        assert ref is not None, kind
        assert ref.key == "/tmp/x"


@pytest.mark.asyncio
async def test_should_avisar_cuando_el_bloque_no_trae_script(tmp_path: Path) -> None:
    """Un bloque `admin_script` sin código es un error de la plantilla, no del script."""
    from server.app.core.sandbox_client import LocalSandboxClient
    from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
        DeterministicExtractionNode,
    )
    from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
        AdminScriptExtractionPipeline,
    )

    spec = _spec_con_script(con_codigo=False)

    fichero = tmp_path / "datos.xlsx"
    fichero.write_bytes(b"x")

    salida = await DeterministicExtractionNode(
        _FactoriaDeUno(AdminScriptExtractionPipeline(client=LocalSandboxClient()))
    )(_estado(spec, str(fichero)))

    avisos = [w.kind for w in salida["warnings"]]
    assert "script_empty" in avisos or "script_not_approved" in avisos


# ---------------------------------------------------------------------------
# El fichero: ya materializado en local, o en el almacén
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_should_leer_el_artefacto_ya_materializado_sin_volver_al_almacen(
    tmp_path: Path,
) -> None:
    """`FileNormalizationNode` ya bajó el fichero: pedirlo otra vez es pagarlo dos veces.

    La convención la fijó VER.4 y la usa el nodo de extracción: `bucket` vacío y la ruta
    entera en `key` significa «esto ya es un fichero local».
    """
    from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
        AdminScriptExtractionPipeline,
    )
    from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef

    fichero = tmp_path / "materializado.xlsx"
    fichero.write_bytes(b"contenido local")

    class _AlmacenQueNoSeDebeUsar:
        async def get(self, key: str) -> bytes:
            raise AssertionError("no debería pedirse al almacén un fichero ya local")

    recibido: dict = {}

    class _Espia:
        async def execute_extraction_script(self, **kwargs):
            from datetime import datetime, timezone

            from server.app.modules.redaccion.pipelines.contracts import (
                ExtractionProvenance,
                ExtractionResult,
            )

            recibido.update(kwargs)
            return ExtractionResult(provenance=ExtractionProvenance(
                pipeline_id="espia", source_ref="espia",
                extracted_at=datetime.now(timezone.utc),
            ))

    await AdminScriptExtractionPipeline(
        client=_Espia(), storage=_AlmacenQueNoSeDebeUsar()
    ).extract_async(ExtractionInput(
        source_kind="admin_script",
        file_ref=StorageRef(bucket="", key=str(fichero)),
        options={"code": _CODIGO, "approved": True},
    ))

    assert recibido["file_bytes"] == b"contenido local"
    assert recibido["file_name"] == "materializado.xlsx"
