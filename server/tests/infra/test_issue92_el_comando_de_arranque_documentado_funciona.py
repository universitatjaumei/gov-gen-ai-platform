"""El comando de arranque que documentan README e INSTALACION es el que arranca de verdad.

**El fallo (issue #92).** Los dos decían, desde `server/`:

    uv run uvicorn app.main:app --port 8000

y eso **no arranca**: `ModuleNotFoundError: No module named 'server'`. La aplicación importa
`server.app.*` en absoluto, así que necesita la raíz del repositorio en el camino de importación,
y desde `server/` la raíz no está. Medido: desde la raíz con `--project server` importa; desde
`server/`, no.

Es la primera instrucción que ejecuta quien clona el repositorio. Con el repositorio abierto eso
es cualquiera, y se encuentra un error en el primer paso sin pista de que la causa es el
directorio desde el que ejecuta.

**Por qué el comando documentado tiene que ser el de la imagen.** Dos formas de arrancar la misma
aplicación es cómo una se queda atrás sin que nadie lo note — que es literalmente lo que pasó: el
`Dockerfile` arranca `server.app.main:app` desde la raíz con `PYTHONPATH=/app` y funciona, y la
copia escrita a mano en dos documentos se quedó con la forma vieja.

Así que lo que este fichero cruza no es «el comando es correcto» —eso exigiría arrancarlo— sino
**que el módulo que dicen los documentos es el mismo que el de la imagen**, que es el dato que
divergió.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DOCKERFILE = RAIZ / "Dockerfile"
DOCUMENTOS = (RAIZ / "README.md", RAIZ / "docs" / "INSTALACION.md")

#: Cualquier invocación de uvicorn escrita en un documento, con su ruta de módulo.
_ARRANQUE = re.compile(r"uvicorn\s+([\w.]+:\w+)")


def _modulo_del_dockerfile() -> str:
    """La ruta de módulo del `CMD`, que es la que arranca en producción."""
    texto = DOCKERFILE.read_text(encoding="utf-8")
    encontrado = re.search(r'CMD\s*\[\s*"uvicorn"\s*,\s*"([\w.]+:\w+)"', texto)
    assert encontrado, "no encuentro el `CMD` de uvicorn en el `Dockerfile`"
    return encontrado.group(1)


def _arranques_documentados() -> list[tuple[str, str]]:
    """`(documento, módulo)` de cada invocación de uvicorn escrita en la documentación."""
    salida: list[tuple[str, str]] = []
    for doc in DOCUMENTOS:
        for modulo in _ARRANQUE.findall(doc.read_text(encoding="utf-8")):
            salida.append((doc.name, modulo))
    return salida


def test_el_medidor_encuentra_los_dos_lados() -> None:
    """Un guardarraíl que no encuentra comandos pasa en verde sin comprobar nada."""
    assert _modulo_del_dockerfile()
    assert len(_arranques_documentados()) >= 2, (
        f"sólo veo {_arranques_documentados()} invocaciones de uvicorn en la documentación"
    )


def test_la_documentacion_arranca_el_mismo_modulo_que_la_imagen() -> None:
    """El cruce que faltaba, y que habría cazado esto el día que se escribió."""
    de_la_imagen = _modulo_del_dockerfile()
    discrepan = [
        f"{doc} dice «{modulo}»"
        for doc, modulo in _arranques_documentados()
        if modulo != de_la_imagen
    ]
    assert discrepan == [], (
        f"la imagen arranca «{de_la_imagen}» y la documentación dice otra cosa:\n  "
        + "\n  ".join(discrepan)
        + "\n\nDos formas de arrancar la misma aplicación es cómo una se queda atrás. El "
        "comando documentado tiene que ser el de la imagen."
    )


def test_ningun_documento_arranca_desde_server() -> None:
    """La otra mitad del defecto: el módulo correcto **desde el directorio equivocado**.

    `server.app.main:app` ejecutado desde `server/` falla igual, porque lo que falta es la raíz
    en el camino de importación. Así que no basta con que el módulo cuadre: el bloque tiene que
    ejecutarse desde la raíz.
    """
    culpables: list[str] = []
    for doc in DOCUMENTOS:
        lineas = doc.read_text(encoding="utf-8").splitlines()
        # Dentro de cada bloque de código, el último `cd` antes del `uvicorn` manda.
        directorio = ""
        dentro = False
        for numero, linea in enumerate(lineas, 1):
            if linea.strip().startswith("```"):
                dentro = not dentro
                directorio = ""
                continue
            if not dentro:
                continue
            cd = re.search(r"\bcd\s+(\S+)", linea)
            if cd:
                directorio = cd.group(1)
            if "uvicorn" in linea and directorio.startswith("server"):
                culpables.append(f"{doc.name}:{numero} arranca desde «{directorio}»")
    assert culpables == [], (
        "hay un arranque de uvicorn dentro de un bloque que se ha movido a `server/`:\n  "
        + "\n  ".join(culpables)
        + "\n\nDesde ahí la raíz no está en el camino de importación y falla con "
        "`ModuleNotFoundError: No module named 'server'`."
    )
