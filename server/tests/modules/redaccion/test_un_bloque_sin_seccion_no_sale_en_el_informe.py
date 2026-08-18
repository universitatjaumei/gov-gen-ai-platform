"""Un bloque que no está en ninguna sección desaparece del informe, y nadie avisa (SEG.5).

Encontrado montando el informe de seguimiento de doctorado a mano: la plantilla se publicó, el
grafo extrajo las nueve tablas, el modelo escribió las nueve valoraciones, todas se aprobaron, la
vista previa respondió 200 y el DOCX se descargó... con las dos secciones **vacías**. El motivo:
`sections[].block_ids` estaba a cero, y tanto la vista previa como el ensamblado recorren las
secciones y sólo pintan los bloques que la sección enumera.

El fallo no salía por ninguna parte: ni error, ni aviso, ni cero bloques en el manifiesto. Sólo un
informe corto con aspecto de estar bien, que es la peor forma de fallar en un informe
institucional.

`_embed_script_block` ya había aprendido esto en PRO.3 —añade a mano el bloque del script a la
primera sección— pero la regla vivía en ese único sitio en vez de estar comprobada.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
from server.app.modules.redaccion.contracts.template import SectionContract
from server.app.modules.redaccion.services.draft_validator import DraftValidator
from server.app.modules.redaccion.services.estructura_del_informe import bloques_sin_seccion
from server.app.modules.redaccion.services.llm_spec_service import _build_system_prompt

# --------------------------------------------------------------------------------------------
# La función pura
# --------------------------------------------------------------------------------------------


def _seccion(id_: str, *block_ids: str) -> SectionContract:
    return SectionContract(id=id_, title=id_, order=1, block_ids=list(block_ids))


class _Bloque:
    def __init__(self, id_: str, kind: str = "STATIC_TEXT") -> None:
        self.id = id_
        self.kind = kind


def test_los_bloques_enumerados_por_alguna_seccion_no_son_huerfanos():
    secciones = [_seccion("s1", "a", "b"), _seccion("s2", "c")]
    assert bloques_sin_seccion(secciones, [_Bloque("a"), _Bloque("b"), _Bloque("c")]) == []


def test_el_bloque_que_ninguna_seccion_enumera_sale_en_la_lista():
    secciones = [_seccion("s1", "a")]
    assert bloques_sin_seccion(secciones, [_Bloque("a"), _Bloque("b")]) == ["b"]


def test_sin_secciones_todos_los_bloques_son_huerfanos_y_en_orden_de_declaracion():
    """Es exactamente el caso de la plantilla montada a mano: secciones sin `block_ids`."""
    assert bloques_sin_seccion([], [_Bloque("z"), _Bloque("a")]) == ["z", "a"]


def test_una_plantilla_vacia_no_tiene_huerfanos():
    """El constructor guarda `spec_json: {}` antes de tener bloques: eso no es un fallo."""
    assert bloques_sin_seccion([], []) == []


def test_el_bloque_que_produce_datos_o_frena_el_flujo_no_necesita_seccion():
    """No se imprimen: el `TABLE` pinta los datos y la puerta de revisión no es contenido.

    Meter el `DETERMINISTIC_DATA` en una sección además duplicaría la tabla.
    """
    fuera = [
        _Bloque("t_datos", "DETERMINISTIC_DATA"),
        _Bloque("t_limpio", "DATA_TRANSFORM"),
        _Bloque("puerta", "REVIEW_GATE"),
    ]
    assert bloques_sin_seccion([], fuera) == []


def test_la_tabla_y_la_valoracion_si_necesitan_seccion():
    """Son lo que se lee. Es el caso que dejó el informe de doctorado con dos secciones vacías."""
    imprimibles = [_Bloque("tabla_1_2", "TABLE"), _Bloque("v_1_2", "AI_ASSISTED_TEXT")]
    assert bloques_sin_seccion([], imprimibles) == ["tabla_1_2", "v_1_2"]


def test_una_seccion_que_referencia_un_bloque_inexistente_no_inventa_huerfanos():
    assert bloques_sin_seccion([_seccion("s1", "a", "fantasma")], [_Bloque("a")]) == []


# --------------------------------------------------------------------------------------------
# El borrador del LLM
# --------------------------------------------------------------------------------------------


def _borrador(sections: list[dict], blocks: list[dict]) -> ReportTemplateDraft:
    return ReportTemplateDraft(
        proposed_profile="DOCTORATE_PROGRAM_REPORT",
        proposed_sections=sections,
        proposed_blocks=blocks,
        proposed_inputs={"required_slots": [], "optional_slots": []},
        rationale="prueba",
        model_used="modelo-de-prueba",
        prompt_version="v1",
    )


_EXTRACCION = {
    "id": "t_matricula",
    "kind": "DETERMINISTIC_DATA",
    "title": "Matrícula",
    "source_pipeline": "md_table",
    "options": {"table": "Tabla 1.2"},
}
_TABLA = {
    "id": "tabla_matricula",
    "kind": "TABLE",
    "title": "Evolución de la matrícula",
    "data_block_ref": "t_matricula",
}


def test_el_validador_rechaza_un_borrador_con_un_bloque_fuera_de_toda_seccion():
    resultado = DraftValidator().validate(
        _borrador(
            [{"id": "s1", "title": "Criterio 1", "order": 1, "block_ids": []}],
            [_EXTRACCION, _TABLA],
        )
    )

    assert resultado.ok is False
    assert any("tabla_matricula" in e.message for e in resultado.errors)
    assert any("secc" in e.message.lower() or "section" in e.message.lower()
               for e in resultado.errors)


def test_el_validador_acepta_el_borrador_cuando_la_seccion_enumera_sus_bloques():
    resultado = DraftValidator().validate(
        _borrador(
            [{"id": "s1", "title": "Criterio 1", "order": 1,
              "block_ids": ["tabla_matricula"]}],
            [_EXTRACCION, _TABLA],
        )
    )

    assert resultado.ok is True, [e.message for e in resultado.errors]


def test_el_prompt_del_modelo_exige_asignar_cada_bloque_a_una_seccion():
    """Si la regla no está en el prompt, el modelo propone plantillas que no se pueden pintar."""
    instrucciones = _build_system_prompt("user").lower()

    assert "block_ids" in instrucciones
    assert "every block" in instrucciones


# --------------------------------------------------------------------------------------------
# La publicación de la versión
# --------------------------------------------------------------------------------------------


def _spec(sections: list[dict], blocks: list[dict]) -> dict:
    return {
        "sections": sections,
        "blocks": blocks,
        "input_contract": {"required_slots": [], "optional_slots": []},
        "ui_contract": {
            "wizard_steps": [],
            "manual_fields": [],
            "dropzones": [],
            "block_editor_enabled": True,
            "ai_review_panel_enabled": True,
            "preview_layout": "markdown",
        },
        "ai_block_policy": "allowed",
        "review_policy": "required",
        "export_policy": "docx",
    }


def _app_con_plantilla() -> FastAPI:
    from server.app.routers.redaccion.hub_redaccion_router import router as hub_router

    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=MagicMock())  # la plantilla existe
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = []
    session_mock.execute = AsyncMock(return_value=resultado)
    session_mock.add = MagicMock()
    session_mock.commit = AsyncMock()

    async def _sesion():
        yield session_mock

    async def _usuario():
        return UserInfo(user_id=str(uuid.uuid4()), email="t@example.com", role="admin")

    app = FastAPI()
    app.include_router(hub_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = _sesion
    app.dependency_overrides[get_current_user] = _usuario
    return app


def test_publicar_una_version_con_bloques_huerfanos_responde_422():
    """El autor de la plantilla se enterará aquí o no se enterará nunca."""
    app = _app_con_plantilla()
    with TestClient(app) as client:
        respuesta = client.post(
            f"/api/v1/hub/redaccion/templates/{uuid.uuid4()}/versions",
            params={"dry_run": "true"},
            json={"spec_json": _spec(
                [{"id": "s1", "title": "Criterio 1", "order": 1, "block_ids": []}],
                [_EXTRACCION, _TABLA],
            )},
        )

    assert respuesta.status_code == 422, respuesta.text
    assert "tabla_matricula" in respuesta.text


def test_publicar_una_version_con_todos_los_bloques_asignados_pasa():
    app = _app_con_plantilla()
    with TestClient(app) as client:
        respuesta = client.post(
            f"/api/v1/hub/redaccion/templates/{uuid.uuid4()}/versions",
            params={"dry_run": "true"},
            json={"spec_json": _spec(
                [{"id": "s1", "title": "Criterio 1", "order": 1,
                  "block_ids": ["tabla_matricula"]}],
                [_EXTRACCION, _TABLA],
            )},
        )

    assert respuesta.status_code == 201, respuesta.text
