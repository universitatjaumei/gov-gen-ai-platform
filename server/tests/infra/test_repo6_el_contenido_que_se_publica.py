"""REPO.6 — lo que contiene el repositorio el día que se abre.

La purga de GitHub verificó que el historial no arrastra los 92 volcados: eso cierra **de dónde
viene** el repositorio. Esto mira **qué contiene hoy**, que es lo otro que se publica al cambiar la
visibilidad y que ningún bloque anterior había barrido entero.

**La distinción registro / superficie viva** es la misma de REPO.3, REPO.4 y REPO.5:
`HISTORIAL.md` y `planificacion/fase1/` **cuentan lo que pasó** y se conservan tal cual —falsear el
registro sería peor que el problema que se arregla—. `PROJECT_STATE.md` **no** es registro: es el
cursor, lo que un lector consulta como verdad presente, y por eso entra en el barrido.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_RAIZ = Path("..")

#: Lo que cuenta lo que pasó. No se barre.
_REGISTRO = ("planificacion/HISTORIAL.md", "planificacion/fase1/")

#: Cualquier correo de la casa. El dominio es el que identifica a una persona real.
_CORREO_INSTITUCIONAL = re.compile(r"\b([a-zA-Z0-9._%+-]+)@uji\.es\b")

#: Las partes locales que SÍ pueden aparecer, cada una con su razón.
#:
#: No es una lista de «correos permitidos» sino de **cadenas que no nombran a nadie**, más el
#: contacto que el mantenedor publica a propósito. Si alguien añade una entrada aquí para callar
#: un rojo, lo que tiene que escribir es por qué esa cadena no identifica a una persona — y si no
#: puede escribirlo, es que sí la identifica.
_PERMITIDAS: dict[str, str] = {
    "fabra": (
        "el contacto del mantenedor, publicado a propósito en README.md y SECURITY.md: un "
        "repositorio abierto sin una dirección a la que escribir no recibe ni avisos de "
        "seguridad"
    ),
    "verif": "cadena de verificación en un .bat de pruebas manuales; no existe como cuenta",
    "noexiste": "literalmente una cuenta que no existe, usada para probar que el login falla",
    "alguien": "marcador de ejemplo en la plantilla de importación de escenarios",
}


def _versionados() -> list[str]:
    """Se pregunta a git, no al disco: lo que importa es lo que recibe quien clona."""
    salida = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in salida.split("\0") if p]


def _es_registro(ruta: str) -> bool:
    return any(ruta.startswith(r) for r in _REGISTRO)


def _es_de_tests(ruta: str) -> bool:
    """Los correos de los tests son sintéticos —`root@`, `x@`, `persona-manual@`— y son ~190.

    Meterlos en `_PERMITIDAS` convertiría la lista en un vertedero y le quitaría el sentido: una
    lista de excepciones sólo vale mientras se pueda leer entera.
    """
    partes = ruta.split("/")
    return (
        "tests" in partes
        or "__tests__" in partes
        or ruta.endswith((".test.ts", ".test.tsx"))
    )


def test_la_superficie_viva_no_nombra_a_ninguna_persona_de_la_casa() -> None:
    """El repositorio se abre, y con él todo lo que un lector consulta como verdad presente.

    El caso que lo motivó: `PROJECT_STATE.md` nombraba a los **seis** probadores del piloto con su
    correo institucional y decía, en el mismo párrafo, que sus seis cuentas son
    superadministradoras de producción **compartiendo una contraseña que no pueden cambiar**. Dato
    personal y mapa de qué atacar a la vez.

    La deuda no se borró —sigue viva, y perderla sería peor—: se conservó **sin las identidades**.
    """
    culpables: list[str] = []
    for ruta in _versionados():
        if _es_registro(ruta) or _es_de_tests(ruta):
            continue
        fichero = _RAIZ / ruta
        try:
            texto = fichero.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binarios: no nombran a nadie
        for numero, linea in enumerate(texto.splitlines(), 1):
            for parte_local in _CORREO_INSTITUCIONAL.findall(linea):
                if parte_local in _PERMITIDAS:
                    continue
                culpables.append(f"{ruta}:{numero} → {parte_local}@uji.es")

    assert not culpables, (
        "La superficie viva nombra a personas de la casa con su correo institucional:\n  - "
        + "\n  - ".join(culpables)
        + "\n\nEl repositorio se va a abrir. Un correo institucional identifica a una persona "
        "real, y junto a lo que el documento diga de ella —qué cuenta tiene, qué poderes— deja "
        "de ser un dato de contacto.\n"
        "Si la cadena no nombra a nadie, va a `_PERMITIDAS` **con la razón escrita**. Si nombra "
        "a alguien, la identidad va a `_local/` y el documento se queda con lo que hacía falta "
        "saber.\n"
        "`HISTORIAL.md` y `planificacion/fase1/` no se barren: son registro."
    )


def test_ningun_script_lleva_la_ruta_de_una_maquina_concreta() -> None:
    """Un script que abre `C:\\Users\\<alguien>\\...` no puede ejecutarlo nadie que clone.

    No es un problema de privacidad sino de que el directorio `scripts/` promete cosas que se
    pueden ejecutar. Los siete que motivaron este test apuntaban todos al mismo fichero de la app
    NiceGUI, retirada el 2026-09-04: no fallaban, es que no había forma de que funcionaran.
    """
    ruta_absoluta = re.compile(r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9._-]+")

    culpables: list[str] = []
    for ruta in _versionados():
        if not ruta.startswith("scripts/"):
            continue
        try:
            texto = (_RAIZ / ruta).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for numero, linea in enumerate(texto.splitlines(), 1):
            if ruta_absoluta.search(linea):
                culpables.append(f"{ruta}:{numero} → {linea.strip()[:90]}")

    assert not culpables, (
        "Scripts que sólo funcionan en la máquina de quien los escribió:\n  - "
        + "\n  - ".join(culpables)
        + "\n\nLo que se publica en `scripts/` se publica como ejecutable. O la ruta entra por "
        "argumento o variable de entorno, o el script no pinta en el repositorio."
    )


#: Salidas guardadas: un fichero con esta forma es la salida de algo, no la entrada de nada.
_EXTENSIONES_DE_VOLCADO = (".txt", ".log", ".out", ".dump")


def test_no_se_publican_volcados_de_ejecuciones() -> None:
    """Dos residuos versionados, y ninguno lo encontró nadie ejecutando nada.

    `server/my_errores.txt` eran 90 KB de salida de pytest del 2026-05-02 en UTF-16, con rutas de
    la máquina que la produjo. `frontend/tsc_baseline.txt` era una salida de `tsc` del 2026-05-06
    que **ningún fichero del repositorio menciona**: ni un script, ni un workflow, ni la
    configuración. Lo que `_local/README.md` describe palabra por palabra.

    **Se mira la forma, no el nombre.** La primera versión de este test buscaba las palabras
    `volcado`, `salida_de`, `my_errores`… y se puso roja con `scripts/volcado_piloto.sh`, que es
    la **herramienta que hace** un volcado, no un volcado. Un criterio por nombre acusa a lo que
    se llama parecido y deja pasar lo que se llama distinto, que es justo lo que se cuela.
    """
    sospechosos = [
        ruta
        for ruta in _versionados()
        if ruta.endswith(_EXTENSIONES_DE_VOLCADO) and not _es_de_tests(ruta)
    ]

    assert not sospechosos, (
        "Salidas guardadas, versionadas:\n  - "
        + "\n  - ".join(sospechosos)
        + "\n\nVan a `_local/`, que está ignorada y existe para esto. En el repositorio ocupan, "
        "nadie las lee y arrastran rutas de la máquina que las produjo.\n"
        "Si de verdad es una ENTRADA y no una salida —un fichero que algo del repositorio lee—, "
        "la prueba es enseñar quién lo lee: si no lo lee nadie, es una salida."
    )


def test_el_codigo_de_conducta_existe_y_se_puede_encontrar() -> None:
    """Lo único del juego estándar que faltaba, y el que decide qué pasa cuando alguien se pasa.

    Un repositorio institucional que se abre va a recibir gente de fuera. Sin este documento, la
    respuesta a un incidente se improvisa, y quien lo sufre no sabe ni a quién escribir — por eso
    se comprueba también que lleve un contacto y que se llegue a él desde `CONTRIBUTING.md`.
    """
    codigo = _RAIZ / "CODE_OF_CONDUCT.md"
    assert codigo.exists(), (
        "No hay `CODE_OF_CONDUCT.md`. Es lo único del juego estándar que falta: LICENSE, README, "
        "CONTRIBUTING, SECURITY, DCO, CODEOWNERS y las plantillas de issue y PR sí están."
    )

    texto = codigo.read_text(encoding="utf-8")
    assert _CORREO_INSTITUCIONAL.search(texto), (
        "`CODE_OF_CONDUCT.md` no dice a quién se le reporta un incidente. Un código de conducta "
        "sin dirección de contacto no se puede cumplir: describe qué está mal y no dice qué "
        "hacer cuando pasa."
    )

    contribuyendo = (_RAIZ / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "CODE_OF_CONDUCT.md" in contribuyendo, (
        "`CONTRIBUTING.md` no enlaza el código de conducta. Quien va a contribuir lee "
        "CONTRIBUTING; un documento que no se encuentra desde ahí no lo lee nadie."
    )
