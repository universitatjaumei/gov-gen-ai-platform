"""APER.24 — el README de `automatia-shared` no puede anunciar módulos que no existen.

APER.12 retiró de ese paquete `contracts/`, `core/`, `security/`, `utils/` y `validators/` —el
81% de un paquete muerto heredado de AutomatIA— y **el README se quedó describiéndolos**, con un
ejemplo de uso que importaba `automatia_shared.validators`. Quien lo copiara se comía un
`ModuleNotFoundError`.

**Y no es un fichero cualquiera.** El manifiesto lo declara como `readme`, así que es la
documentación que viaja con el paquete publicado: anunciaba una API que la misma PR borraba. Lo
encontró la revisión automática de la PR #50.

Este guardarraíl comprueba lo único que se puede comprobar de una prosa: que **cada módulo que
nombra exista**. No vigila que el texto esté bien escrito —eso no lo caza ningún test— sino que
la lista de contenidos y los ejemplos no se queden hablando de lo que ya se fue, que es
exactamente lo que pasó.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PAQUETE = RAIZ / "shared" / "automatia_shared"
README = RAIZ / "shared" / "README.md"

#: Lo que se retiró en APER.12. Si alguno reaparece aquí sin volver al paquete, es que el texto
#: ha vuelto a describir el pasado como si fuera el presente.
RETIRADOS = ("contracts", "core", "security", "utils", "validators")


def _modulos_que_nombra(texto: str) -> set[str]:
    """Los `automatia_shared.X` del README, vengan de un import o de una tabla."""
    return set(re.findall(r"automatia_shared\.([a-z_][a-z0-9_]*)", texto))


def _existe(modulo: str) -> bool:
    """Un submódulo existe si es un paquete con `__init__.py` o un fichero suelto."""
    return (PAQUETE / modulo / "__init__.py").is_file() or (
        PAQUETE / f"{modulo}.py"
    ).is_file()


def test_cada_modulo_que_nombra_existe() -> None:
    nombrados = _modulos_que_nombra(README.read_text(encoding="utf-8"))
    assert nombrados, (
        "el README no nombra ni un módulo. O ha cambiado de forma, y entonces este guardarraíl "
        "ya no mira nada, o se ha quedado vacío."
    )
    fantasmas = sorted(m for m in nombrados if not _existe(m))
    assert not fantasmas, (
        f"El README de `automatia-shared` anuncia módulos que no existen: {fantasmas}. Es el "
        "`readme` declarado en el manifiesto, o sea la documentación que se publica con el "
        "paquete: quien copie el ejemplo se lleva un `ModuleNotFoundError`."
    )


def test_los_retirados_en_aper12_no_vuelven_como_prosa() -> None:
    """Lo contrario del test anterior: que el texto no los dé por vivos sin estarlo."""
    texto = README.read_text(encoding="utf-8")
    resucitados = [
        nombre
        for nombre in RETIRADOS
        if re.search(rf"^[-*|]\s*\**`?automatia_shared\.{nombre}", texto, re.MULTILINE)
        or re.search(rf"^[-*]\s*\**{nombre}/\**", texto, re.MULTILINE)
    ]
    assert not resucitados, (
        f"El README vuelve a listar como contenido lo que APER.12 retiró: {resucitados}. "
        "Mencionarlos para contar que se fueron está bien; listarlos como si estuvieran, no."
    )


def test_el_manifiesto_sigue_declarando_este_readme() -> None:
    """Si deja de declararlo, este guardarraíl vigila un fichero decorativo y hay que decirlo."""
    manifiesto = (RAIZ / "shared" / "pyproject.toml").read_text(encoding="utf-8")
    assert 'readme = "README.md"' in manifiesto, (
        "`shared/pyproject.toml` ya no declara `README.md` como `readme`. Entonces este fichero "
        "deja de ser documentación publicada y la razón de este test cambia."
    )
