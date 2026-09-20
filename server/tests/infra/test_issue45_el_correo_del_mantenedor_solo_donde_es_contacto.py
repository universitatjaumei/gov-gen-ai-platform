"""Issue #45 — el correo del mantenedor sólo donde es contacto, no repartido por fixtures.

**No era una fuga.** Es el correo de contacto público de `SECURITY.md`, del
`CODE_OF_CONDUCT.md` y de los metadatos de los paquetes, y ahí tiene que estar: alguien tiene
que poder avisar de un fallo de seguridad.

El problema era el **ruido**. Repartido por *fixtures* aparecía 74 veces en 47 ficheros, así que
cualquier búsqueda de datos personales devolvía 74 resultados; y quien hace una búsqueda que
siempre devuelve 74 resultados deja de mirarlos uno a uno, que es exactamente cómo se esconde un
positivo de verdad. Con el repositorio público habrá más de esas búsquedas, propias y ajenas.

Hay precedente en el proyecto: el defecto por omisión de `DEV_ADMIN_EMAIL` era este mismo correo
y se cambió a `admin@example.local` justamente para que un fork no arrancara sembrando la
identidad de otra persona. Las *fixtures* pasan ahora a ese mismo valor, así que el sistema y sus
pruebas dicen lo mismo.

**La regla es la misma que la de los `TODO` en la issue #46**: lo que va entre comillas
invertidas es una **cita** y no cuenta. Sin esa distinción, esto se habría llevado por delante
justo la documentación que explica el defecto —`test_seed_environment_gate.py` y
`test_ais2_nada_institucional_en_el_principal.py` citan el valor viejo para contar que todo fork
arrancaba sembrando la identidad del mantenedor— y también el registro de `PRUEBAS_MANUALES.md`,
que anota con qué sesión se verificó cada cosa y en qué fecha.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
CORREO = "fabra@uji.es"

_CITA = re.compile(r"`[^`]*`")

#: Donde el correo **no** puede estar como dato: código, fixtures y guiones de prueba.
ZONAS_LIMPIAS = (
    RAIZ / "server" / "app",
    RAIZ / "server" / "tests",
    RAIZ / "pruebas_manuales",
    RAIZ / "frontend" / "src",
    RAIZ / "mcp_server" / "app",
)

#: Donde sí, porque es contacto o metadatos del paquete. Se listan para que añadir uno sea una
#: decisión y no un descuido.
DE_CONTACTO = (
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "README.md",
    "docs/LICENCIA_ES.md",
    "docs/PRESENTACION_PROYECTO.md",
    "server/pyproject.toml",
    "mcp_server/pyproject.toml",
    "frontend/package.json",
)


def _como_dato(fichero: Path) -> list[str]:
    """Las líneas donde el correo aparece fuera de comillas invertidas."""
    try:
        texto = fichero.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    encontradas = []
    for numero, linea in enumerate(texto.splitlines(), 1):
        if CORREO in _CITA.sub("", linea):
            encontradas.append(f"{fichero.relative_to(RAIZ)}:{numero}")
    return encontradas


@pytest.mark.parametrize("zona", ZONAS_LIMPIAS, ids=lambda z: z.name)
def test_no_esta_como_dato_en_el_codigo_ni_en_las_fixtures(zona: Path) -> None:
    if not zona.is_dir():
        pytest.skip(f"{zona} no existe en este árbol")
    culpables: list[str] = []
    for fichero in zona.rglob("*"):
        if not fichero.is_file():
            continue
        if any(p in fichero.parts for p in ("__pycache__", "node_modules", ".venv")):
            continue
        # Este fichero se excluye a sí mismo: necesita la constante con el correo para poder
        # buscarla. Es el mismo caso que `test_aper19`, que se salta a sí mismo al comprobar
        # que nadie referencia el servicio que retiró.
        if fichero.name == Path(__file__).name:
            continue
        culpables.extend(_como_dato(fichero))

    assert not culpables, (
        f"El correo del mantenedor aparece como dato en {zona.name}:\n  - "
        + "\n  - ".join(culpables)
        + f"\n\nEn fixtures y semillas va `{'admin@example.local'}`, que es lo que usa la "
        "semilla de desarrollo. El correo real se queda sólo donde es contacto."
    )


def test_sigue_estando_donde_hace_falta() -> None:
    """Lo contrario, y no es simetría: sin contacto, `SECURITY.md` no sirve para nada.

    Un guardarraíl que sólo empujara a quitar el correo acabaría quitándolo también de donde
    tiene que estar, y nadie podría avisar de un fallo de seguridad.
    """
    faltan = [
        nombre
        for nombre in DE_CONTACTO
        if (RAIZ / nombre).is_file() and CORREO not in (RAIZ / nombre).read_text(encoding="utf-8")
    ]
    assert not faltan, (
        f"estos ficheros han perdido el correo de contacto: {faltan}. Ahí sí tiene que estar: "
        "es por donde se avisa de un fallo de seguridad o se pregunta por la licencia."
    )


def test_las_citas_historicas_siguen_contando_lo_que_paso() -> None:
    """Explicar un defecto pasado exige nombrarlo, y eso no es ruido: es la razón del arreglo."""
    for ruta in (
        "server/tests/unit/test_seed_environment_gate.py",
        "server/tests/infra/test_ais2_nada_institucional_en_el_principal.py",
    ):
        fichero = RAIZ / ruta
        assert CORREO in fichero.read_text(encoding="utf-8"), (
            f"{ruta} ha dejado de contar que el defecto por omisión de `DEV_ADMIN_EMAIL` era el "
            "correo del mantenedor. Esa frase es la razón de que se cambiara; borrarla para que "
            "una búsqueda dé menos resultados es perder el porqué."
        )
        assert not _como_dato(fichero), (
            f"en {ruta} el correo ha dejado de ir entre comillas invertidas, así que ahora "
            "cuenta como dato."
        )
