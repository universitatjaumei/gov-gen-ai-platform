"""REG.9 — cuando el contrato rechaza algo, dice por qué y adónde ir.

`extra="forbid"` cumple la regla del bloque: mandar el prompt no registra nada, falla. Pero el
mensaje que produce Pydantic es este:

    Extra inputs are not permitted [type=extra_forbidden, loc=('prompt',)]

Dice **qué** y no dice **por qué**, y esa diferencia tiene consecuencias concretas. Quien integra
lee eso y saca la conclusión razonable: «al esquema le falta un campo, pido que lo añadan». Y
entonces la conversación que hay que tener es la de explicar, a posteriori y por un canal lento,
que el registro no puede convertirse en un segundo sitio donde viven los datos personales — que
es justo lo que este mensaje puede decir gratis, en el momento y en el sitio donde alguien está
mirando.

Los dos rechazos que se explican son distintos y por eso son dos mensajes:

- **Un campo de contenido** (`prompt`, `payload`, `texto`…): la regla del bloque, con la salida
  buena (`payload_hash`).
- **`organizacion_id`**: no es contenido, es que no se elige. Sale del token, y quien lo manda
  cree estar eligiendo.

Cualquier otro extra recibe el mensaje genérico con el puntero al documento: no vale la pena
adivinar la intención de un campo que nadie ha visto todavía.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

BASE = {
    "ocurrido_en": "2026-09-03T10:30:00+00:00",
    "actor": "u-1",
    "herramienta": "claude-cowork",
    "finalidad": "Revisión de un pliego",
}

DOCUMENTO = "REGISTRO_ACTIVIDAD_IA.md"


def _error(**extra) -> str:
    from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

    with pytest.raises(ValidationError) as excinfo:
        ActividadIAEvent(**BASE, **extra)
    return str(excinfo.value)


class TestElRechazoDeUnCampoDeContenido:

    @pytest.mark.parametrize(
        "campo", ["prompt", "payload", "content", "mensaje", "texto", "respuesta"]
    )
    def test_should_explain_the_rule_instead_of_saying_extra_forbidden(self, campo: str):
        mensaje = _error(**{campo: "lo que se procesó"})

        assert "metadatos" in mensaje, mensaje
        assert campo in mensaje, "el mensaje tiene que nombrar el campo que sobra"

    def test_should_point_at_the_way_to_leave_evidence(self):
        """La salida buena, en el mismo mensaje: si necesitas prueba, el hash.

        Sin esto, quien integra sabe que no puede mandar el texto y no sabe qué hacer en su
        lugar, así que o pide el campo o deja de registrar ese caso.
        """
        mensaje = _error(prompt="lo que se procesó")

        assert "payload_hash" in mensaje
        assert "SHA-256" in mensaje

    def test_should_name_the_document_that_explains_the_whole_contract(self):
        mensaje = _error(prompt="x")

        assert DOCUMENTO in mensaje, (
            "quien se estrella tiene que encontrar el sitio donde se explica, sin preguntar."
        )


class TestElRechazoDeLaOrganizacion:

    def test_should_say_that_the_organisation_comes_from_the_token(self):
        """No es contenido: es que no se elige, y quien lo manda cree estar eligiendo."""
        mensaje = _error(organizacion_id="00000000-0000-0000-0000-000000000010")

        assert "token" in mensaje, mensaje
        assert "organizacion_id" in mensaje
        # Y no el mensaje de contenido, que aquí no viene al caso y confundiría.
        assert "metadatos" not in mensaje


class TestCualquierOtroExtra:

    def test_should_still_reject_it_and_point_at_the_document(self):
        """Sin adivinar la intención de un campo que nadie ha visto todavía."""
        mensaje = _error(un_campo_que_nadie_ha_visto="x")

        assert "un_campo_que_nadie_ha_visto" in mensaje
        assert DOCUMENTO in mensaje


class TestLoQueNoCambia:
    """El arreglo es del mensaje. Lo que el contrato acepta y rechaza sigue igual."""

    def test_should_still_accept_a_valid_event(self):
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        evento = ActividadIAEvent(
            **BASE,
            agente="revisor-de-contratos",
            modelo_usado="claude-opus-5",
            categorias_datos=["datos_identificativos"],
            payload_hash="a" * 64,
        )

        assert evento.actor == "u-1"

    def test_should_still_reject_a_naive_timestamp(self):
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        with pytest.raises(ValidationError):
            ActividadIAEvent(**{**BASE, "ocurrido_en": "2026-09-03T10:30:00"})

    def test_should_still_reject_a_malformed_hash(self):
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        with pytest.raises(ValidationError):
            ActividadIAEvent(**BASE, payload_hash="no-es-un-sha256")


class TestElPunteroDesdeElMCP:

    def test_should_name_the_document_in_the_tool_description(self):
        """Quien llega por MCP no ve nunca la documentación del repositorio.

        El docstring de la tool es lo único que su cliente le muestra, así que el puntero va ahí.
        """
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[3]
        fuente = (raiz / "mcp_server" / "tools" / "actividad.py").read_text(
            encoding="utf-8"
        )

        assert DOCUMENTO in fuente

    def test_should_point_at_the_catalogue_endpoint(self):
        """Y al catálogo de categorías, que es lo que evita que invente códigos (REG.8)."""
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[3]
        fuente = (raiz / "mcp_server" / "tools" / "actividad.py").read_text(
            encoding="utf-8"
        )

        assert "/actividad/categorias" in fuente
