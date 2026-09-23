"""REPO.3 — el índice de `docs/` no enlaza al vacío, y nada activo cita lo retirado.

El triaje editorial de REPO.3 retira documentos, y retirar un documento rompe dos cosas que
nadie ve hasta que alguien pincha: el **índice** (`docs/README.md`), que lo sigue enlazando, y
los **documentos vivos** que lo citaban. Las dos son exactamente el fallo que un repositorio
público paga en credibilidad: un enlace muerto en la primera página que alguien abre.

Estos dos tests son el guardarraíl del triaje, y valen igual para el siguiente: no llevan la
lista de lo retirado en REPO.3 escrita a mano —eso caducaría—, sino que comprueban la propiedad
que debe seguir siendo cierta siempre.

**Qué entra en el barrido y qué no.** Se recorre `docs/` entero, menos los ficheros que son
**registro del pasado**: `INVENTARIO_RETIRADA_LEGACY.md` puede nombrar lo retirado porque su
función es justamente eso. `planificacion/` no se recorre —su `HISTORIAL.md` y sus planes de fase
cerrados son registro por definición—. Lo que no puede pasar es que un documento **activo** mande
a leer un fichero que no está.

**Y «no está» significa «no lo tiene quien clona», no «no está en mi disco»**: se pregunta a
`git ls-files`. El porqué, que es un fallo real de la primera versión, en `_versionados()`.
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

_DOCS = Path("../docs")
_RAIZ = Path("..")


@lru_cache(maxsize=1)
def _versionados() -> frozenset[str]:
    """Los ficheros que git tiene, en POSIX y relativos a la raíz del repositorio.

    **Se pregunta a git y no al disco, y eso es el arreglo de un fallo real.** La primera
    versión de estos tests usaba `Path.is_file()`, pasaba en local y **se puso roja en CI**:
    `docs/README.md` enlazaba `EU_GOVERNANCE_CONCEPT_NOTE.md` y `EU_GOVERNANCE_TOPICS.md`, que
    existen en el disco del mantenedor pero **no en el repositorio** —están excluidos en
    `.git/info/exclude`, que es por clon y no viaja—.

    O sea que el test pasaba por el entorno y no por el árbol, que es justo lo que este
    proyecto llama «el medidor miente antes que el sistema». La propiedad que hay que
    comprobar no es «el fichero está en mi disco» sino **«lo tiene quien clona»**, y eso sólo
    lo sabe git.
    """
    salida = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return frozenset(p for p in salida.split("\0") if p)


def _esta_en_el_repositorio(destino: Path) -> bool:
    """`destino` es una ruta del sistema; se traduce a la forma que usa `git ls-files`."""
    try:
        relativa = destino.resolve().relative_to(_RAIZ.resolve())
    except ValueError:
        return False
    return relativa.as_posix() in _versionados()


#: Enlaces markdown a un `.md`, capturando sólo la ruta y descartando ancla y título.
_ENLACE_MD = re.compile(r"\]\(\s*<?([^)>\s#]+\.md)(?:#[^)>\s]*)?>?\s*(?:\"[^\"]*\")?\s*\)")

#: Ficheros que son REGISTRO del pasado: pueden nombrar lo retirado, es su función.
_SON_REGISTRO = (
    "planificacion/HISTORIAL.md",
    "docs/INVENTARIO_RETIRADA_LEGACY.md",
)


def _documentos_de_docs() -> list[Path]:
    return sorted(p for p in _DOCS.rglob("*.md") if "node_modules" not in p.parts)


def _es_registro(ruta: Path) -> bool:
    posix = ruta.as_posix()
    return any(posix.endswith(r) for r in _SON_REGISTRO)


class TestElIndiceNoEnlazaAlVacio:
    """`docs/README.md` es la puerta de entrada: un enlace roto ahí se ve antes que el código."""

    def test_should_not_link_a_document_that_does_not_exist(self):
        readme = _DOCS / "README.md"
        assert readme.is_file(), "no hay docs/README.md, que es el índice"

        rotos: list[str] = []
        for destino in _ENLACE_MD.findall(readme.read_text(encoding="utf-8")):
            if destino.startswith(("http://", "https://")):
                continue
            if not _esta_en_el_repositorio(readme.parent / destino):
                rotos.append(destino)

        assert rotos == [], (
            "docs/README.md enlaza ficheros que no existen:\n  " + "\n  ".join(rotos)
        )


class TestNingunDocumentoActivoCitaUnoRetirado:
    """Un documento vivo que manda a leer lo que ya no está hace perder el tiempo a quien lo lee.

    No se comprueba contra una lista de retirados: se comprueba que **todo** enlace relativo
    entre documentos de `docs/` resuelve. Así el test no caduca cuando el próximo triaje retire
    otra cosa.
    """

    def test_should_resolve_every_relative_link_between_documents(self):
        rotos: list[str] = []
        for doc in _documentos_de_docs():
            if _es_registro(doc):
                continue
            for destino in _ENLACE_MD.findall(doc.read_text(encoding="utf-8")):
                if destino.startswith(("http://", "https://")):
                    continue
                if not _esta_en_el_repositorio(doc.parent / destino):
                    rotos.append(f"{doc.as_posix()} → {destino}")

        assert rotos == [], (
            "documentos activos que citan ficheros inexistentes:\n  " + "\n  ".join(rotos)
        )


class TestLosDosDocumentosDeMcpSeUnificaron:
    """REPO.3 pide unificar `MCP_SERVER.md` y `mcp.md`, que se solapaban.

    Se comprueba por ausencia del segundo y no por el contenido del primero: lo que el índice
    señalaba era la **duplicidad**, y dos páginas para lo mismo divergen sin que nada avise.
    """

    def test_should_keep_a_single_document_about_the_mcp_server(self):
        assert not (_DOCS / "mcp.md").exists(), (
            "`docs/mcp.md` sigue ahí: se solapaba con `MCP_SERVER.md` y el índice ya lo señalaba"
        )
        assert (_DOCS / "MCP_SERVER.md").is_file(), "falta el documento unificado MCP_SERVER.md"


@pytest.mark.parametrize(
    "retirado",
    [
        "CAMBIOS_ARQUITECTURA.md",
        "CAMBIOS_PLANIFICACION.md",
        "PRUEBAS_PENDIENTES.md",
        "PLAN_CHATBOTS_E_INGESTA_LOCAL.md",
        # Añadido el 2026-09-23 (issue #127). Describía un gestor híbrido con flujos por
        # arrastrar y soltar, Celery, Playwright en el navegador de la persona y generación de
        # scripts en tiempo de ejecución: cinco cosas que contradicen decisiones tomadas. Lo
        # sustituye `DECISION_TRAMITES_ASISTIDOS.md`.
        "GESTOR_EXPEDIENTES.md",
    ],
)
def test_should_have_withdrawn_the_spent_documents(retirado: str):
    """Los que se retiran, con la razón en el commit y el resumen en el historial.

    Se listan aquí a propósito, al contrario que en los tests de arriba: es el criterio de done
    de **este** prompt, no una propiedad permanente, y sirve para que el triaje no quede a medias.
    """
    assert not (_DOCS / retirado).exists(), f"docs/{retirado} sigue en el árbol"
