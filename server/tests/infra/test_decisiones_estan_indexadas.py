"""Una decisión escrita y no indexada es una decisión que nadie encuentra.

El proyecto tenía seis `docs/DECISION_*.md` sueltas, sin número y sin un sitio donde verlas
juntas. Cuatro declaraban `Fecha` y `Estado` y dos no, así que ni siquiera se podía saber de un
vistazo cuáles seguían vigentes.

`docs/DECISIONES.md` es el registro, y este test es lo que impide que vuelva a pasar: si alguien
escribe una decisión nueva y no la indexa, o la indexa sin declarar su estado, la suite se pone
roja.

**Por qué importa el estado y no sólo la existencia.** La decisión 2 —modelos de embedding y
reranker— sigue aceptada, pero el reranker se apagó por medición en HIB.A. Sin ese matiz en el
registro, alguien lo daría por encendido y mediría contra un sistema que no es el que corre.

Mismo patrón que `test_mt7_el_inventario_esta_escrito.py` y
`test_especificaciones_no_miente.py`: el documento es la única página donde algo se puede
consultar, y sólo sigue valiendo mientras algo lo obligue.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

#: `server/tests/infra/` → tres niveles arriba. Con `assert`, porque un test que recorre un
#: directorio inexistente pasa en verde sin mirar nada (la lección del guardarraíl de USR.5).
RAIZ = Path(__file__).resolve().parents[3]
assert (RAIZ / "docs").is_dir(), f"la raíz no es la que se cree: {RAIZ}"

REGISTRO = RAIZ / "docs" / "DECISIONES.md"

#: Los estados admitidos. Se comprueba el **comienzo** de la línea de estado, no el texto entero:
#: «aceptada y aplicada» o «sustituida por la decisión 7» son estados legítimos con matiz, y
#: exigir una de tres palabras exactas obligaría a perder el matiz o a mentir.
#: En masculino y femenino: `DECISION_RENDERIZADO_RASTREO` dice «decidido con la medición
#: delante», y exigir el género sería exigir una redacción, no un estado.
_ESTADOS = (
    "aceptada",
    "aceptado",
    "sustituida",
    "sustituido",
    "revertida",
    "revertido",
    "decidida",
    "decidido",
    "propuesta",
    "propuesto",
)


def _decisiones() -> list[Path]:
    encontradas = sorted((RAIZ / "docs").glob("DECISION_*.md"))
    assert encontradas, (
        "no se ha encontrado ninguna `docs/DECISION_*.md`. O se han renombrado todas —y entonces "
        "hay que actualizar este test y el registro— o la ruta está mal, que es peor porque "
        "dejaría el test pasando en el vacío."
    )
    return encontradas


@pytest.fixture(scope="module")
def registro() -> str:
    assert REGISTRO.is_file(), (
        "falta `docs/DECISIONES.md`, que es el registro de decisiones de arquitectura y el único "
        "sitio donde se ven juntas con su estado."
    )
    return REGISTRO.read_text(encoding="utf-8")


class TestElRegistroEstaCompleto:

    @pytest.mark.parametrize("decision", _decisiones(), ids=lambda p: p.stem)
    def test_should_be_listed_in_the_register(self, decision: Path, registro: str):
        assert decision.name in registro, (
            f"`{decision.name}` no está en `docs/DECISIONES.md`. Una decisión escrita y no "
            "indexada es una decisión que nadie encuentra: quien venga detrás implementará lo "
            "contrario de buena fe."
        )

    def test_should_not_list_a_decision_that_does_not_exist(self, registro: str):
        """Al revés también: el registro no puede apuntar a un fichero retirado."""
        nombres = set(re.findall(r"\(DECISION_[A-Z_]+\.md\)", registro))
        muertas = [
            n for n in nombres if not (RAIZ / "docs" / n.strip("()")).is_file()
        ]
        assert not muertas, (
            f"el registro apunta a decisiones que no existen: {sorted(muertas)}. Si una se "
            "retiró, la entrada no se borra: se marca `Estado: revertida`, porque borrar el "
            "razonamiento pierde la prueba de que la alternativa se consideró."
        )


class TestCadaDecisionSeIdentifica:
    """Sin fecha y sin estado, un documento de decisión no dice si sigue vigente."""

    @pytest.mark.parametrize("decision", _decisiones(), ids=lambda p: p.stem)
    def test_should_declare_a_date(self, decision: Path):
        texto = decision.read_text(encoding="utf-8")
        assert re.search(r"\*\*Fecha\*\*:?\s*\d{4}-\d{2}-\d{2}", texto), (
            f"`{decision.name}` no declara `**Fecha**: AAAA-MM-DD`. La fecha es lo que permite "
            "leer dos decisiones que se contradicen y saber cuál manda."
        )

    @pytest.mark.parametrize("decision", _decisiones(), ids=lambda p: p.stem)
    def test_should_declare_a_known_state(self, decision: Path):
        texto = decision.read_text(encoding="utf-8")
        encontrado = re.search(r"\*\*Estado\*\*:?\s*(.{2,60})", texto)
        assert encontrado, (
            f"`{decision.name}` no declara `**Estado**`. Sin él no se sabe si sigue vigente, y el "
            "registro tendría que inventárselo."
        )
        estado = encontrado.group(1).strip().lower()
        assert estado.startswith(_ESTADOS), (
            f"`{decision.name}` declara el estado «{estado[:40]}», que no empieza por ninguno de "
            f"{list(_ESTADOS)}. El matiz detrás es bienvenido —«aceptada y aplicada», «sustituida "
            "por la 7»—, pero la primera palabra tiene que ser legible de un vistazo."
        )


class TestSeLlegaAlRegistro:

    @pytest.mark.parametrize("desde", ["docs/README.md", "CONTRIBUTING.md"])
    def test_should_be_linked_from(self, desde: str):
        contenido = (RAIZ / desde).read_text(encoding="utf-8")
        assert "DECISIONES.md" in contenido, (
            f"`{desde}` no enlaza el registro de decisiones. El índice de documentación es donde "
            "se busca, y `CONTRIBUTING.md` es donde alguien lee que su propuesta puede necesitar "
            "una."
        )

    def test_should_say_when_an_adr_is_needed(self, registro: str):
        """El registro tiene que decir el criterio, no sólo listar.

        Sin criterio, o nadie escribe ADR o se escribe uno por cada corrección de un defecto, y
        las dos cosas lo vacían de valor.
        """
        assert "## Cuándo hace falta un ADR" in registro
        assert "HISTORIAL.md" in registro, (
            "el registro tiene que decir dónde va lo que **no** merece ADR; si no, la frontera "
            "queda a criterio de cada uno."
        )
