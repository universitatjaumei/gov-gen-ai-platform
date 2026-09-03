"""El plan de Fase 1 está partido en ficheros, y el índice no puede quedarse corto.

`Plan_TDD_Fase1.md` eran **27.449 líneas en un solo fichero**. Era lo único del método que no
escalaba a más manos: no se puede revisar en un *pull request*, ni comentar por línea, ni saber
por dónde empezar. Ahora cada bloque y cada fase viven en `planificacion/fase1/`, y el fichero
original es el índice.

Un índice incompleto es peor que no tenerlo: quien lo lea creerá que el bloque que falta no
existe, y en un plan eso significa reimplementar algo ya planificado o dar por cerrado algo que no
lo está. Este test lo comprueba **en las dos direcciones**.

Mismo patrón que `test_especificaciones_no_miente.py` y `test_decisiones_estan_indexadas.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

#: `server/tests/infra/` → tres niveles arriba, con `assert`: un test que recorre un directorio
#: inexistente pasa en verde sin mirar nada.
RAIZ = Path(__file__).resolve().parents[3]
assert (RAIZ / "planificacion").is_dir(), f"la raíz no es la que se cree: {RAIZ}"

INDICE = RAIZ / "planificacion" / "Plan_TDD_Fase1.md"
FASE1 = RAIZ / "planificacion" / "fase1"


def _partes() -> list[Path]:
    encontradas = sorted(FASE1.glob("*.md"))
    assert encontradas, (
        "`planificacion/fase1/` está vacío o no existe. Si el plan se ha vuelto a juntar en un "
        "fichero, hay que retirar este test; si la ruta cambió, esto estaría pasando en el vacío."
    )
    return encontradas


@pytest.fixture(scope="module")
def indice() -> str:
    assert INDICE.is_file(), "falta `planificacion/Plan_TDD_Fase1.md`, que es el índice del plan"
    return INDICE.read_text(encoding="utf-8")


def _enlazados(indice: str) -> set[str]:
    return set(re.findall(r"\(fase1/([^)]+)\)", indice))


class TestElIndiceEstaCompleto:

    @pytest.mark.parametrize("parte", _partes(), ids=lambda p: p.stem)
    def test_should_link_every_file(self, parte: Path, indice: str):
        assert parte.name in _enlazados(indice), (
            f"`{parte.name}` existe en `planificacion/fase1/` y el índice no lo enlaza. Quien "
            "lea el índice creerá que ese bloque no existe, y en un plan eso significa "
            "reimplementar algo ya planificado."
        )

    def test_should_not_link_a_file_that_is_gone(self, indice: str):
        nombres = {p.name for p in _partes()}
        muertos = sorted(_enlazados(indice) - nombres)
        assert not muertos, (
            f"el índice enlaza ficheros que no existen: {muertos}. Un enlace muerto en el índice "
            "del plan manda a buscar un bloque que se movió o se renombró."
        )


class TestCadaParteEsLegible:
    """Lo que de verdad rompería un corte mal puesto."""

    @pytest.mark.parametrize("parte", _partes(), ids=lambda p: p.stem)
    def test_should_close_every_code_fence(self, parte: Path):
        """Los prompts viven en vallas ```markdown; una impar significa un prompt partido.

        Es la comprobación que justifica el corte: los encabezados de nivel 1 del fichero están
        casi todos **dentro** de vallas —los prompts empiezan por `# PROMPT ...`— y cortar sin
        respetarlas partiría un prompt por la mitad sin que nada se quejara.
        """
        vallas = len(
            re.findall(r"^\s*```", parte.read_text(encoding="utf-8"), re.MULTILINE)
        )
        assert vallas % 2 == 0, (
            f"`{parte.name}` tiene {vallas} vallas de código: impar significa que un prompt "
            "quedó partido entre dos ficheros."
        )

    @pytest.mark.parametrize("parte", _partes(), ids=lambda p: p.stem)
    def test_should_start_with_its_own_heading(self, parte: Path):
        primera = parte.read_text(encoding="utf-8").split("\n", 1)[0]
        assert re.match(r"^#{1,2}\s+(BLOQUE|Bloque|FASE|Fase|Subfase)\s+", primera), (
            f"`{parte.name}` no empieza por el encabezado de su sección, sino por "
            f"«{primera[:60]}». Cada parte tiene que ser legible por sí sola."
        )


class TestElIndiceSigueSiendoUtil:

    def test_should_stay_small_enough_to_read(self, indice: str):
        """El sentido del corte era que el índice se pueda leer de una sentada.

        Si vuelve a crecer hasta cientos de kilobytes, el problema ha vuelto: alguien está
        escribiendo prompts en el índice en vez de en el fichero de su bloque.
        """
        kb = len(indice.encode("utf-8")) // 1024
        assert kb < 120, (
            f"el índice del plan ha crecido a {kb} KB. El corte se hizo porque 1.379 KB en un "
            "fichero no se pueden revisar ni comentar; los prompts van en "
            "`planificacion/fase1/<bloque>.md`, no aquí."
        )

    def test_should_point_at_the_cursor_and_the_spec(self, indice: str):
        """Las dos preguntas que no contesta un plan, y a dónde mandar a quien las trae."""
        assert "PROJECT_STATE.md" in indice, "el índice no dice dónde está el cursor"
        assert "ESPECIFICACIONES.md" in indice, (
            "el índice no manda a la especificación. «Qué falta» y «qué garantiza el sistema» son "
            "preguntas distintas, y confundirlas es lo que este documento provoca si no lo dice."
        )
