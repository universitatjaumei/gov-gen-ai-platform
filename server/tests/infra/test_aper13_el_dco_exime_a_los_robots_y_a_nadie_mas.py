"""APER.13 — el DCO exime a los robots, y la exención no se puede ensanchar sin que se note.

**Por qué existe la exención.** El DCO certifica «I have the right to submit it under the open
source license indicated in the file». Eso lo afirma **una persona** sobre código que aporta. Un
robot que sube un número de versión en un `uv.lock` no aporta código de nadie: reordena una
resolución de dependencias. No hay autoría que certificar.

Y exigírselo tenía un coste medido: el 2026-09-19 había **trece pull requests de Dependabot
abiertas a la vez y ninguna se podía mezclar**, todas en rojo por la misma línea. Un guardarraíl
que hace imposible el camino bueno se acaba apagando entero, y eso sí habría sido perder el DCO.

**Qué vigila este fichero.** Que la exención sea exactamente la que se decidió: por **correo** del
autor y sólo para cuentas de robot, que se **diga en el registro** cuando se aplica, y que para
las personas no cambie nada. Lo último es lo que importa: la política sigue valiendo para el
mantenedor —quien se exceptúa de su propia política la deja sin fuerza— y por eso no vale
comprobar el nombre, que lo puede poner cualquiera en un commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
DCO = RAIZ / ".github" / "workflows" / "dco.yml"


@pytest.fixture(scope="module")
def guion() -> str:
    """El guion del paso que comprueba las firmas."""
    datos = yaml.safe_load(DCO.read_text(encoding="utf-8"))
    pasos = datos["jobs"]["signed-off-by"]["steps"]
    for paso in pasos:
        if "Signed-off-by" in (paso.get("name") or ""):
            return paso["run"]
    raise AssertionError("no encuentro el paso que comprueba el Signed-off-by")


class TestLaExencionEsLaQueSeDecidio:

    def test_se_exime_por_correo_y_no_por_nombre(self, guion: str) -> None:
        """El nombre de autor lo elige quien commitea; el correo de la cuenta, no.

        Con una comprobación por nombre, cualquiera podría firmar como «dependabot[bot]» y
        saltarse el DCO. Es la diferencia entre una exención y un agujero.
        """
        assert '"$correo"' in guion, (
            "La exención no mira el correo del autor. Si mira el nombre, cualquiera puede "
            "ponerse el del robot y saltarse el DCO."
        )
        assert "[bot]@users.noreply.github.com" in guion, (
            "La exención no está acotada a los correos de cuenta de robot de GitHub."
        )

    def test_la_exencion_se_dice_en_el_registro(self, guion: str) -> None:
        """Una exención que no se ve en el registro es una que nadie vuelve a revisar."""
        assert "::notice::" in guion and "exento" in guion, (
            "Cuando se salta un commit, el paso tiene que decirlo en el registro."
        )

    def test_los_saltados_se_cuentan_aparte(self, guion: str) -> None:
        """Sumarlos a los revisados haría que el resumen dijera «todos firmados» de commits
        que nadie ha comprobado."""
        assert "saltados" in guion, "no se lleva cuenta de los commits exentos"
        assert "saltados=$((saltados + 1))" in guion


class TestParaLasPersonasNoCambiaNada:

    def test_sigue_exigiendo_la_firma(self, guion: str) -> None:
        assert "Signed-off-by:" in guion and "falta Signed-off-by" in guion, (
            "El paso ha dejado de exigir la firma."
        )

    def test_sigue_exigiendo_que_la_firma_sea_del_autor(self, guion: str) -> None:
        """Firmar con el nombre de otro no certifica nada."""
        assert "no coincide con el autor" in guion

    def test_sigue_poniendose_rojo(self, guion: str) -> None:
        assert "exit 1" in guion, "el paso ya no falla cuando encuentra un commit sin firmar"

    def test_sigue_revisando_las_dos_ramas_y_las_pull_requests(self) -> None:
        """La política valía también para `main` y `desarrollo`, y eso no lo toca APER.13."""
        datos = yaml.safe_load(DCO.read_text(encoding="utf-8"))
        disparadores = datos[True] if True in datos else datos["on"]
        assert set(disparadores["push"]["branches"]) == {"main", "desarrollo"}
        assert disparadores["pull_request"]["branches"] == ["main"]


class TestLaRazonEstaEscrita:

    def test_el_fichero_explica_por_que_se_exime(self) -> None:
        """Sin la razón, dentro de un año esto parece un atajo que alguien metió con prisa."""
        prosa = " ".join(
            linea.lstrip("# ").strip()
            for linea in DCO.read_text(encoding="utf-8").splitlines()
            if linea.lstrip().startswith("#")
        )
        prosa = " ".join(prosa.split())
        for idea in ("robot", "certific", "responsabilidad"):
            assert idea in prosa, f"la razón de la exención no menciona «{idea}»"

    def test_contributing_lo_cuenta(self) -> None:
        """Quien contribuye lee `CONTRIBUTING.md`, no el YAML del workflow."""
        texto = (RAIZ / "CONTRIBUTING.md").read_text(encoding="utf-8")
        assert "dependabot" in texto.lower(), (
            "`CONTRIBUTING.md` no menciona la exención: quien lea que «cada commit va firmado» "
            "y vea un commit de robot sin firmar en el historial pensará que la política no se "
            "cumple."
        )
