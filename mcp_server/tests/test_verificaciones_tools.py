"""VAS.4 — las tres verificaciones como tools MCP.

El arnés es el de REG.4: se habla streamable HTTP contra la aplicación ASGI, así que se comprueba
el camino de verdad —incluido que el token de cada cliente llega al endpoint— y no la función de
la tool llamada a mano.

Lo que este fichero defiende, además de que cada tool llame a su endpoint:

**Los esquemas declaran los campos.** Es la lección de REG.7: una tool con un `dict` opaco deja a
quien la usa adivinando nombres de la prosa, y su `additionalProperties: true` contradice al
servidor. Aquí se comprueba propiedad por propiedad.

**El token es el de cada petición**, como en REG.4: el servidor remoto no tiene credencial propia.
"""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from tests.test_actividad_tools import (  # noqa: F401 — se reutiliza el arnés de REG.4
    API,
    HOST,
    PAT_UNO,
    _config,
    _llama,
    _payload,
    _texto,
    servidor_mcp,
)

NORMA = "https://normativa.uji.es/html/reglament-permanencia.html"


class TestVerificarCitas:

    @respx.mock
    async def test_should_call_the_citations_endpoint(self):
        ruta = respx.post(f"{API}/api/v1/verificaciones/citas").mock(
            return_value=httpx.Response(
                200,
                json={
                    "cumple": True,
                    "texto_resultante": "ok",
                    "citas_validas": [NORMA],
                    "citas_invalidas": [],
                    "remisiones_despojadas": 0,
                    "anclas_degradadas": 0,
                },
            )
        )

        async with servidor_mcp() as app:
            resultado = await _llama(
                app,
                "verificar_citas",
                {
                    "texto": f"Segun [art. 4]({NORMA}).",
                    "fuentes_permitidas": [{"url": NORMA, "titulo": "Reglamento"}],
                },
                pat=PAT_UNO,
            )

        assert _payload(resultado)["cumple"] is True
        enviado = json.loads(ruta.calls.last.request.content)
        assert enviado["fuentes_permitidas"][0]["url"] == NORMA
        assert ruta.calls.last.request.headers["authorization"] == f"Bearer {PAT_UNO}"

    @respx.mock
    async def test_should_leave_out_the_optional_message(self):
        """Lo que nadie declara no viaja: `mensaje_sin_respuesta` es opcional en el contrato."""
        ruta = respx.post(f"{API}/api/v1/verificaciones/citas").mock(
            return_value=httpx.Response(
                200,
                json={
                    "cumple": False,
                    "texto_resultante": "no",
                    "citas_validas": [],
                    "citas_invalidas": [],
                    "remisiones_despojadas": 0,
                    "anclas_degradadas": 0,
                },
            )
        )

        async with servidor_mcp() as app:
            await _llama(
                app,
                "verificar_citas",
                {"texto": "x", "fuentes_permitidas": []},
                pat=PAT_UNO,
            )

        assert set(json.loads(ruta.calls.last.request.content)) == {
            "texto",
            "fuentes_permitidas",
        }


class TestConsultarVigencia:

    @respx.mock
    async def test_should_query_by_document_id(self):
        ruta = respx.get(f"{API}/api/v1/verificaciones/vigencia").mock(
            return_value=httpx.Response(
                200, json={"document_id": "abc", "necesita_aviso": False, "aviso": None}
            )
        )

        async with servidor_mcp() as app:
            resultado = await _llama(
                app, "consultar_vigencia", {"document_id": "abc"}, pat=PAT_UNO
            )

        assert _payload(resultado)["document_id"] == "abc"
        assert ruta.calls.last.request.url.params["document_id"] == "abc"

    @respx.mock
    async def test_should_query_by_url_without_sending_the_other_parameter(self):
        """Mandar los dos es 422 en el servidor, así que sólo viaja el que se dio.

        Con `document_id=None` en la cadena de consulta, el servidor vería dos parámetros y
        rechazaría la petición — un 422 provocado por el cliente.
        """
        ruta = respx.get(f"{API}/api/v1/verificaciones/vigencia").mock(
            return_value=httpx.Response(200, json={"document_id": "abc"})
        )

        async with servidor_mcp() as app:
            await _llama(app, "consultar_vigencia", {"url": NORMA}, pat=PAT_UNO)

        params = ruta.calls.last.request.url.params
        assert params["url"] == NORMA
        assert "document_id" not in params


class TestAuditarCodigo:

    @respx.mock
    async def test_should_call_the_audit_endpoint(self):
        ruta = respx.post(f"{API}/api/v1/verificaciones/codigo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "approved": False,
                    "risk_level": "CRITICAL",
                    "puede_revisarse": False,
                    "findings": [],
                    "confidence": 0.0,
                    "code_sha256": "a" * 64,
                },
            )
        )

        async with servidor_mcp() as app:
            resultado = await _llama(
                app,
                "auditar_codigo",
                {"codigo": "eval('1')", "finalidad": "Antes de compartirlo"},
                pat=PAT_UNO,
            )

        assert _payload(resultado)["risk_level"] == "CRITICAL"
        enviado = json.loads(ruta.calls.last.request.content)
        assert enviado == {"codigo": "eval('1')", "finalidad": "Antes de compartirlo"}

    @respx.mock
    async def test_should_serve_the_toolbox(self):
        respx.get(f"{API}/api/v1/verificaciones/codigo/reglas").mock(
            return_value=httpx.Response(
                200,
                json={
                    "modulos_permitidos": ["json"],
                    "capacidades_denegadas": ["os"],
                    "reglas": [],
                    "version_auditor": "abc123",
                },
            )
        )

        async with servidor_mcp() as app:
            resultado = await _llama(app, "reglas_de_auditoria", {}, pat=PAT_UNO)

        assert _payload(resultado)["version_auditor"] == "abc123"

    async def test_should_not_gate_the_audit_behind_a_confirmation(self):
        """Se llama antes de compartir cada script: una puerta delante la haría inútil.

        Y no muta nada, que es el criterio con el que `update_chatbot` sí la tiene.
        """
        from http_server import build_http_server

        servidor = build_http_server(_config())
        auditar = next(
            t for t in await servidor.list_tools() if t.name == "auditar_codigo"
        )

        assert "confirm" not in json.dumps(auditar.inputSchema).lower()


class TestLosEsquemasDeclaranElContrato:
    """La lección de REG.7, aplicada de entrada y no después de que duela."""

    async def test_should_expose_the_four_tools(self):
        from http_server import build_http_server

        servidor = build_http_server(_config())
        nombres = {t.name for t in await servidor.list_tools()}

        assert {
            "verificar_citas",
            "consultar_vigencia",
            "auditar_codigo",
            "reglas_de_auditoria",
        } <= nombres

    @pytest.mark.parametrize(
        ("tool", "propiedades", "obligatorias"),
        [
            (
                "verificar_citas",
                {"texto", "fuentes_permitidas", "mensaje_sin_respuesta"},
                {"texto", "fuentes_permitidas"},
            ),
            ("consultar_vigencia", {"document_id", "url"}, set()),
            ("auditar_codigo", {"codigo", "finalidad"}, {"codigo"}),
        ],
    )
    async def test_should_declare_every_field(
        self, tool: str, propiedades: set[str], obligatorias: set[str]
    ):
        from http_server import build_http_server

        servidor = build_http_server(_config())
        esquema = next(
            t for t in await servidor.list_tools() if t.name == tool
        ).inputSchema

        assert set(esquema["properties"]) == propiedades
        assert set(esquema.get("required", [])) == obligatorias

    async def test_should_describe_what_the_type_cannot_say(self):
        """«Sólo estas cuentan como fundamento» y «no se guarda» no salen de `str`."""
        from http_server import build_http_server

        servidor = build_http_server(_config())
        tools = {t.name: t for t in await servidor.list_tools()}

        citas = tools["verificar_citas"].inputSchema["properties"]
        assert "fundamento" in citas["fuentes_permitidas"]["description"]

        codigo = tools["auditar_codigo"].inputSchema["properties"]
        assert "SHA-256" in codigo["codigo"]["description"]


class TestElTokenSigueSiendoElDeCadaPeticion:

    @respx.mock
    async def test_should_carry_each_client_token(self):
        """Lo mismo que REG.4, y con dos clientes a la vez por la misma razón."""
        import asyncio

        ruta = respx.get(f"{API}/api/v1/verificaciones/codigo/reglas").mock(
            return_value=httpx.Response(
                200,
                json={
                    "modulos_permitidos": [],
                    "capacidades_denegadas": [],
                    "reglas": [],
                    "version_auditor": "x",
                },
            )
        )

        from tests.test_actividad_tools import PAT_DOS

        async with servidor_mcp() as app:
            await asyncio.gather(
                _llama(app, "reglas_de_auditoria", {}, pat=PAT_UNO),
                _llama(app, "reglas_de_auditoria", {}, pat=PAT_DOS),
            )

        tokens = {llamada.request.headers["authorization"] for llamada in ruta.calls}
        assert tokens == {f"Bearer {PAT_UNO}", f"Bearer {PAT_DOS}"}

    @respx.mock
    async def test_should_fail_readably_without_a_token(self):
        ruta = respx.get(f"{API}/api/v1/verificaciones/codigo/reglas")

        async with servidor_mcp() as app:
            resultado = await _llama(app, "reglas_de_auditoria", {}, pat=None)

        assert resultado.get("isError"), resultado
        assert "PAT" in _texto(resultado)
        assert not ruta.called
