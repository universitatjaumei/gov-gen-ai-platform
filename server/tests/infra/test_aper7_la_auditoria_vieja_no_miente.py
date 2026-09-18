"""APER.7 — la auditoría del 2026-08-10 no puede volver a dar por abierto lo que está cerrado.

**Hallazgo C5 de la auditoría previa a abrir el repositorio.** `docs/AUDITORIA_PRE_DEPLOY.md`
llevaba mes y medio describiendo, hallazgo por hallazgo, cosas como que `SANDBOX_MODE=local` no
tenía gate de producción. Lo tiene desde SEC.8.3 y un segundo desde SEC.9.6. Con el repositorio a
punto de hacerse público, eso era publicar una lista de vulnerabilidades ya cerradas con el
aspecto de estar vivas, en el documento con más pinta de autoridad del árbol.

**Qué vigila esto, y por qué es la forma que funciona.** No comprueba la prosa —eso no lo puede
hacer un test, y es la lección de `test_especificaciones_no_miente.py`—. Comprueba la **deriva
estructural**, que es la que ocurrió: que cada hallazgo del cuerpo tenga un estado y que cada
estado de la tabla corresponda a un hallazgo. Es el mismo patrón que el inventario de routers de
SEC.9.5: se **recorre** el documento en vez de mantener a mano una lista que alguien tiene que
acordarse de ampliar, así que un hallazgo nuevo sin estado pone esto rojo sin que nadie haga nada.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
AUDITORIA = RAIZ / "docs" / "AUDITORIA_PRE_DEPLOY.md"

MARCADORES = ("✅", "⏳", "▶", "ℹ️")

#: Un hallazgo del cuerpo: `- ✅ **AL-1 · …`, `▶ **I4 · …`, `- ⏳ **M2** · …` o, el resuelto y
#: tachado, `- ✅ ~~**I5 · …`.
_HALLAZGO = re.compile(
    r"^(?:- )?(?P<marca>[✅⏳▶]|ℹ️)?\s*~?~?\*\*(?P<id>(?:CR|AL|ME|B|I|M)-?\d+)\*?\*? ·",
    re.MULTILINE,
)


@pytest.fixture(scope="module")
def texto() -> str:
    assert AUDITORIA.is_file(), "no está docs/AUDITORIA_PRE_DEPLOY.md"
    return AUDITORIA.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cuerpo(texto: str) -> str:
    """Del cuerpo hacia abajo: la tabla de estado vive por encima de «## 1. Seguridad»."""
    return texto[texto.index("## 1. Seguridad") :]


def _ids_de_la_tabla(texto: str) -> set[str]:
    """Los hallazgos que la tabla de estado declara, con su marcador."""
    tabla = texto[: texto.index("## 1. Seguridad")]
    ids: set[str] = set()
    for linea in tabla.splitlines():
        if not linea.startswith("| "):
            continue
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if len(celdas) < 2:
            continue
        m = re.match(r"^(?P<id>(?:CR|AL|ME|B|I|M)-?\d+) ·", celdas[0])
        if m and any(marca in celdas[1] for marca in MARCADORES):
            ids.add(m.group("id"))
    return ids


class TestCadaHallazgoDiceEnQueEstado:

    def test_ningun_hallazgo_del_cuerpo_se_queda_sin_marcador(self, cuerpo: str) -> None:
        """Un hallazgo sin marcador se lee como abierto, que es lo que pasó durante mes y medio."""
        sin_marcar = [
            m.group("id") for m in _HALLAZGO.finditer(cuerpo) if not m.group("marca")
        ]
        assert not sin_marcar, (
            f"Estos hallazgos no dicen en qué estado están: {sorted(set(sin_marcar))}. "
            "Sin marcador se leen como abiertos, y este documento va a ser público."
        )

    def test_todo_hallazgo_del_cuerpo_esta_en_la_tabla(
        self, texto: str, cuerpo: str
    ) -> None:
        en_tabla = _ids_de_la_tabla(texto)
        en_cuerpo = {m.group("id") for m in _HALLAZGO.finditer(cuerpo)}
        faltan = en_cuerpo - en_tabla
        assert not faltan, (
            f"Estos hallazgos están en el cuerpo y no en la tabla de estado: {sorted(faltan)}. "
            "La tabla es lo que se lee primero."
        )

    def test_la_tabla_no_inventa_hallazgos(self, texto: str, cuerpo: str) -> None:
        en_tabla = _ids_de_la_tabla(texto)
        en_cuerpo = {m.group("id") for m in _HALLAZGO.finditer(cuerpo)}
        sobran = en_tabla - en_cuerpo
        assert not sobran, (
            f"La tabla declara el estado de hallazgos que no están en el cuerpo: {sorted(sobran)}"
        )

    def test_hay_bastantes_hallazgos_para_que_esto_signifique_algo(
        self, cuerpo: str
    ) -> None:
        """Un guardarraíl que no mira nada pasa en verde.

        Si un cambio de formato rompiera la expresión regular, los tres tests de arriba pasarían
        sobre un conjunto vacío y nadie se enteraría. La auditoría tenía 39 hallazgos.
        """
        encontrados = {m.group("id") for m in _HALLAZGO.finditer(cuerpo)}
        assert len(encontrados) >= 30, (
            f"Sólo se han reconocido {len(encontrados)} hallazgos en el cuerpo, y había 39. "
            "Probablemente ha cambiado el formato y esta comprobación ha dejado de mirar."
        )


class TestSeSabeQueEsEsteDocumento:
    """Lo que evita que se lea como el estado actual del sistema."""

    def test_la_cabecera_dice_que_es_historico(self, texto: str) -> None:
        cabeza = texto[: texto.index("## 1. Seguridad")]
        prosa = " ".join(cabeza.split())
        assert "registro histórico" in prosa, (
            "La cabecera no dice que este documento sea un registro histórico: se leerá como el "
            "estado actual, que es exactamente el hallazgo C5."
        )

    def test_la_cabecera_remite_a_donde_esta_la_verdad_de_hoy(self, texto: str) -> None:
        cabeza = texto[: texto.index("## 1. Seguridad")]
        for destino in ("ESPECIFICACIONES.md", "PROJECT_STATE.md"):
            assert destino in cabeza, (
                f"La cabecera no remite a {destino}, así que quien busque el estado actual se "
                "queda aquí."
            )
