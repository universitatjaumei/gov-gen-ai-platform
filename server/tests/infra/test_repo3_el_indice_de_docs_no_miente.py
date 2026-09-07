"""REPO.3 — el índice de `docs/` no enlaza al vacío, y nada activo cita lo retirado.

El triaje editorial de REPO.3 retira documentos, y retirar un documento rompe dos cosas que
nadie ve hasta que alguien pincha: el **índice** (`docs/README.md`), que lo sigue enlazando, y
los **documentos vivos** que lo citaban. Las dos son exactamente el fallo que un repositorio
público paga en credibilidad: un enlace muerto en la primera página que alguien abre.

Estos dos tests son el guardarraíl del triaje, y valen igual para el siguiente: no llevan la
lista de lo retirado en REPO.3 escrita a mano —eso caducaría—, sino que comprueban la propiedad
que debe seguir siendo cierta siempre.

**Por qué el segundo test mira `planificacion/` además de `docs/`.** Lo retirado se resume en
`HISTORIAL.md`, así que el historial **sí** puede nombrarlo: es su registro. Lo que no puede
pasar es que un documento **activo** mande a leer un fichero que ya no está. Por eso el historial
y los planes de fase quedan fuera del barrido y `docs/` entra entero.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_DOCS = Path("../docs")
_RAIZ = Path("..")

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
            if not (readme.parent / destino).resolve().is_file():
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
                if not (doc.parent / destino).resolve().is_file():
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
    ],
)
def test_should_have_withdrawn_the_spent_documents(retirado: str):
    """Los cuatro que REPO.3 retira, con la razón en el commit y el resumen en el historial.

    Se listan aquí a propósito, al contrario que en los tests de arriba: es el criterio de done
    de **este** prompt, no una propiedad permanente, y sirve para que el triaje no quede a medias.
    """
    assert not (_DOCS / retirado).exists(), f"docs/{retirado} sigue en el árbol"
