"""INF.10 — el copiloto sabe en qué informe está.

En las pruebas del 2026-08-20 el usuario le preguntó «no sé dónde aprobar los bloques» y no
obtuvo respuesta: el copiloto responde con RAG sobre la documentación del proyecto y no sabía
nada del informe que había delante. El legacy sí lo tenía —`client_app/app/core/state.py:79`:
los datos cargados se publican al estado «para que el Copiloto conozca las columnas
disponibles»—.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from server.app.modules.redaccion.services.contexto_del_informe import contexto_del_informe

WS = uuid.uuid4()


class _RepoDeUno:
    def __init__(self, valor):
        self._valor = valor

    async def get(self, _id):
        return self._valor

    async def list(self, _id):
        return self._valor


def _workspace(status="in_review", inputs=None, warnings=None):
    return SimpleNamespace(
        id=WS,
        status=status,
        template_version_id=uuid.uuid4(),
        inputs_json=inputs if inputs is not None else {"datos": {"path": "x"}},
        warnings_json=warnings or [],
    )


def _bloque(block_id, kind, status):
    return SimpleNamespace(block_id=block_id, kind=kind, status=status)


def _version(requeridos=("datos",)):
    return SimpleNamespace(
        spec_json={
            "input_contract": {
                "required_slots": [{"slot_id": s, "kind": "csv", "label": {}} for s in requeridos],
                "optional_slots": [],
            }
        }
    )


async def _contexto(workspace, bloques, version=None):
    return await contexto_del_informe(
        workspace_repo=_RepoDeUno(workspace),
        block_repo=_RepoDeUno(bloques),
        template_version_repo=_RepoDeUno(version or _version()),
        workspace_id=WS,
    )


@pytest.mark.asyncio
async def test_should_say_which_blocks_are_waiting_for_a_person():
    """La pregunta del usuario, respondible: dice **qué** hay que aprobar y **dónde**."""
    texto = await _contexto(
        _workspace(),
        [
            _bloque("t_matricula", "DETERMINISTIC_DATA", "extracted"),
            _bloque("v_matricula", "AI_ASSISTED_TEXT", "needs_review"),
        ],
    )

    assert "v_matricula" in texto
    assert "PENDIENTE DE UNA PERSONA" in texto
    assert "panel de revisión" in texto


@pytest.mark.asyncio
async def test_should_list_the_actions_available_on_each_block():
    """Lo que el copiloto puede recomendar sale de `acciones_permitidas`, no de su imaginación."""
    texto = await _contexto(
        _workspace(), [_bloque("v_tesis", "AI_ASSISTED_TEXT", "failed")]
    )

    assert "regenerate" in texto
    # Aprobar un bloque que falló no es una accion posible, así que no se ofrece.
    assert "approve" not in texto


@pytest.mark.asyncio
async def test_should_say_which_input_is_missing():
    texto = await _contexto(
        _workspace(inputs={}), [_bloque("t_datos", "DETERMINISTIC_DATA", "missing_input")]
    )

    assert "faltan por aportar" in texto
    assert "datos" in texto


@pytest.mark.asyncio
async def test_should_say_when_nothing_is_pending():
    texto = await _contexto(
        _workspace(status="assembled"), [_bloque("v_x", "AI_ASSISTED_TEXT", "approved")]
    )

    assert "No queda nada pendiente" in texto


@pytest.mark.asyncio
async def test_should_anonymise_the_warnings():
    """Los avisos los escribe el grafo sobre datos del cliente, y el modelo puede estar en la nube."""
    texto = await _contexto(
        _workspace(warnings=[{"message": "El fichero de 12345678Z (fabra@uji.es) no tiene tablas"}]),
        [_bloque("t_datos", "DETERMINISTIC_DATA", "extracted")],
    )

    assert "12345678Z" not in texto
    assert "fabra@uji.es" not in texto
    # Pero el aviso sigue diciendo algo útil.
    assert "tablas" in texto


@pytest.mark.asyncio
async def test_should_not_send_the_text_the_ai_wrote():
    """Se manda el **estado**, no el contenido: para «dónde apruebo esto» el texto no hace falta,
    y no mandarlo es la diferencia entre un contexto de veinte palabras y uno de veinte mil."""
    bloque = _bloque("v_x", "AI_ASSISTED_TEXT", "needs_review")
    bloque.content_json = {"text": "La matricula desciende un 6 % respecto al curso anterior."}

    texto = await _contexto(_workspace(), [bloque])

    assert "desciende un 6" not in texto


@pytest.mark.asyncio
async def test_should_return_none_without_a_report():
    assert await contexto_del_informe(
        workspace_repo=_RepoDeUno(None),
        block_repo=_RepoDeUno([]),
        template_version_repo=_RepoDeUno(None),
        workspace_id=WS,
    ) is None
