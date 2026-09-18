"""FUN.7 — que `docs/CATALOGO_FUNCIONES.md` no mienta.

El prompt pide que las reglas del auditor se listen **desde el código y no copiadas a mano**, y la
razón es la de siempre en este proyecto: una lista copiada pasa en verde el día que el código
cambia, y entonces el documento que se le da a un equipo externo describe un auditor que no
existe. Es la misma clase de guardarraíl que `test_especificaciones_no_miente.py`: caza la deriva
**estructural**, no la prosa.

Lo que **no** puede comprobar es si la prosa sigue siendo verdad, y por eso el bloque también
escribe la petición explícita a la UADTI en el propio documento: un contraste con las Guías
Operativas Técnicas no lo puede hacer un test.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[3].parent / "docs" / "CATALOGO_FUNCIONES.md"


@pytest.fixture(scope="module")
def documento() -> str:
    assert RUTA.exists(), f"no encuentro {RUTA}"
    return RUTA.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def caja():
    from server.app.modules.redaccion.services.script_auditor import caja_de_herramientas

    return caja_de_herramientas()


class TestLasReglasDelAuditorSalenDelCodigo:

    def test_should_list_every_allowed_module(self, documento, caja):
        """Los 16 módulos permitidos, uno a uno. Si el auditor gana uno y el documento no, un
        equipo externo escribe código que la plataforma rechazaría por una razón que el documento
        no menciona; si lo pierde, escribe código que el documento permite y el auditor no."""
        faltan = [m for m in caja.modulos_permitidos if f"`{m}`" not in documento]

        assert faltan == [], (
            "módulos que el auditor permite y el documento no nombra: "
            f"{faltan}. La lista de §5 se copia del código, no se escribe de memoria."
        )

    def test_should_name_every_denied_capability(self, documento, caja):
        """Y las denegadas. Son muchas y están agrupadas por familia en el documento, pero cada
        una tiene que aparecer: la que falte es la que alguien usará."""
        faltan = [c for c in caja.capacidades_denegadas if f"`{c}`" not in documento]

        assert faltan == [], (
            f"capacidades denegadas que el documento no nombra: {faltan}"
        )

    def test_should_list_every_rule_with_its_level(self, documento, caja):
        """Con su nivel, porque la diferencia entre CRITICAL y WARNING **es** la diferencia entre
        «no se registra» y «se registra y lo mira la revisión posterior»."""
        for regla in caja.reglas:
            assert f"`{regla.id}`" in documento, f"la regla {regla.id} no está en el documento"
            # El nivel tiene que estar en la misma línea de la tabla que el id.
            linea = next(
                (
                    ln
                    for ln in documento.splitlines()
                    if f"`{regla.id}`" in ln and "|" in ln
                ),
                None,
            )
            assert linea is not None, f"la regla {regla.id} no está en la tabla de §5"
            assert regla.nivel.value in linea, (
                f"la regla {regla.id} aparece con un nivel distinto del que tiene el auditor "
                f"({regla.nivel.value}): «{linea.strip()}»"
            )

    def test_should_not_invent_rules_the_auditor_does_not_have(self, documento, caja):
        """La otra mitad: una regla en el documento que el auditor no aplica es una promesa
        falsa, y es peor que una que falte."""
        import re

        ids_reales = {r.id for r in caja.reglas}
        # Los ids de regla son kebab-case y en el documento van en la tabla de §5.
        seccion = documento.split("## 5.")[1].split("## 6.")[0]
        citados = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", seccion))
        # Se filtran los nombres de módulo y capacidad, que comparten la forma.
        candidatos = citados - set(caja.modulos_permitidos) - set(caja.capacidades_denegadas)

        inventados = candidatos - ids_reales

        assert inventados == set(), (
            f"el documento cita reglas que el auditor no tiene: {sorted(inventados)}"
        )


class TestLoQueElDocumentoTieneQueDecir:
    """Las secciones que el prompt exige, comprobadas por su existencia y no por su redacción.

    Un test no puede juzgar prosa. Lo que sí puede es impedir que una sección **desaparezca**, que
    es lo que pasa cuando alguien reescribe el documento y se salta la parte incómoda — y la parte
    incómoda aquí es justamente la que la OIATI tiene que leer.
    """

    @pytest.mark.parametrize(
        "seccion",
        [
            "## 1. Qué es una función, campo a campo",
            "## 2. El ciclo de una versión",
            "## 3. Quién puede qué",
            "## 4. Correspondencia con la Instrucció 02/2026",
            "## 5. La caja de herramientas del auditor",
            "## 6. Llevar tu script al catálogo",
            "## 7. Empaquetar una función",
            "## 8. Ejecutar una función por API",
            "## 9. El puente a Fase 3",
        ],
    )
    def test_should_have_the_section(self, documento, seccion):
        assert seccion in documento

    def test_should_keep_the_honest_difference_with_the_instruccio(self, documento):
        """La diferencia con la regla 2 —el código va a los datos y no al equipo de la persona—
        y la petición explícita de un «sí» a UADTI y OIATI. Es la parte que un resumen
        entusiasta borraría primero."""
        assert "La diferencia honesta con la regla 2" in documento
        assert "UADTI" in documento and "OIATI" in documento
        assert "no un silencio" in documento

    def test_should_ask_the_uadti_to_contrast_the_rules(self, documento):
        assert "Guías Operativas Técnicas" in documento

    def test_should_say_the_trust_boundary_without_softening_it(self, documento):
        """«Corre in-process, sin sandbox, y quien instala responde». Si esta frase se suaviza,
        el primer equipo externo cree que hay un aislamiento que no existe."""
        seccion = documento.split("## 7.")[1].split("## 8.")[0]
        assert "sin sandbox" in seccion
        assert "No hay" in seccion and "aislamiento" in seccion
        assert "pip install" in seccion

    def test_should_state_that_approving_is_not_a_review_outcome(self, documento):
        """El invariante del nivel 2, escrito donde lo va a leer quien revise. Si el documento
        dijera que se «aprueba» una versión, la persona que revisa creería que su firma es lo que
        autoriza el uso."""
        assert "no hay nada que aprobar" in documento

    def test_should_state_that_the_anchor_survives_publishing(self, documento):
        assert "no cambia ninguna plantilla" in documento
