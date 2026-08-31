"""Las dimensiones de los vectores del modelo y de las migraciones no pueden discrepar.

**El defecto que este guardarraíl no habría dejado pasar.** La primera migración del esquema
dejaba `hub_document_chunks.embedding` en `vector(1536)` y ninguna posterior lo corregía,
mientras el modelo declaraba `Vector(1024)`. Resultado: una base creada con
`alembic upgrade head` tenía una columna **en la que la aplicación no puede escribir**, y la
primera ingesta fallaba con «expected 1536 dimensions, not 1024».

Llevaba meses invisible por dos razones que conviene no repetir:

1. La base de desarrollo está en 1024 porque su tabla no nació de la cadena de migraciones, así
   que allí nunca falló nada.
2. `test_migrations_fresh_install.py` comprueba que las columnas **existan** —`"canonical_url"
   in columnas`— pero no su tipo. Un test de esquema que sólo mira nombres deja pasar cualquier
   divergencia de tipo.

Apareció al restaurar el corpus en producción, que es la primera base de este proyecto creada de
verdad sólo con migraciones. Este test lo caza sin base de datos: cruza lo que declara el modelo
con lo que escriben las migraciones.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MODELOS = RAIZ / "server" / "app" / "modules" / "agents_hub" / "database" / "operational_models.py"
MIGRACIONES = RAIZ / "server" / "migrations" / "versions"

#: `Vector(1024)` en el modelo, con el nombre de la columna delante.
#:
#: `.+\]` y no `[^\]]*\]`: la anotación es `Mapped[list[float] | None]` y los corchetes están
#: anidados, así que parar en el primer `]` dejaba el patrón sin casar y los tres tests de abajo
#: pasaban por ausencia de casos — que es la peor forma de pasar.
_EN_MODELO = re.compile(
    r"^\s*(\w+):\s*Mapped\[.+\]\s*=\s*mapped_column\(\s*Vector\((\d+)\)", re.MULTILINE
)

#: Cualquier `vector(N)` o `Vector(N)` en una migración.
_EN_MIGRACION = re.compile(r"[Vv]ector\((\d+)\)")


def _dimensiones_del_modelo() -> dict[str, int]:
    texto = MODELOS.read_text(encoding="utf-8")
    return {nombre: int(dim) for nombre, dim in _EN_MODELO.findall(texto)}


def test_el_modelo_declara_alguna_dimension() -> None:
    """Si esto falla, el patrón dejó de encontrar las columnas y el resto no prueba nada."""
    dims = _dimensiones_del_modelo()
    assert dims, "No se ha encontrado ninguna columna Vector(...) en el modelo"
    assert "embedding" in dims, "Falta la columna `embedding` de los fragmentos"


def test_el_modelo_usa_una_sola_dimension() -> None:
    """Dos dimensiones distintas en el modelo significan dos espacios vectoriales, y comparar
    vectores de espacios distintos da una similitud sin sentido."""
    dims = set(_dimensiones_del_modelo().values())
    assert len(dims) == 1, (
        f"El modelo declara varias dimensiones: {sorted(dims)}. Si es a propósito, este test "
        "tiene que decir por qué; si no, es un espacio vectorial partido en dos."
    )


def test_ninguna_migracion_deja_una_dimension_que_el_modelo_no_use() -> None:
    """El caso real: una migración fijaba 1536 y el modelo pedía 1024.

    Se permite que una migración mencione una dimensión distinta **si otra posterior la
    corrige**, que es exactamente lo que pasa ahora: la primera deja 1536 y
    `e2b3c4d5f6a7` la devuelve a 1024. Lo que no se permite es que el último valor escrito
    para una columna no sea el del modelo.
    """
    esperada = next(iter(set(_dimensiones_del_modelo().values())))

    # Migraciones en orden de aplicación aproximado: por nombre de fichero, que en este
    # proyecto empieza por el identificador de revisión y no da el orden real. Así que en vez
    # de ordenar, se comprueba la propiedad que importa: que exista una migración que fije la
    # dimensión buena para `hub_document_chunks.embedding`.
    corrige = []
    discrepan = []
    for fichero in sorted(MIGRACIONES.glob("*.py")):
        texto = fichero.read_text(encoding="utf-8")
        if "hub_document_chunks" not in texto or "embedding" not in texto:
            continue
        for dim in {int(d) for d in _EN_MIGRACION.findall(texto)}:
            if dim == esperada and "ALTER COLUMN embedding TYPE" in texto:
                corrige.append(fichero.name)
            elif dim != esperada and "ALTER COLUMN embedding TYPE" in texto:
                discrepan.append(f"{fichero.name}: vector({dim})")

    assert corrige, (
        f"Ninguna migración fija `hub_document_chunks.embedding` en vector({esperada}), que es "
        f"lo que declara el modelo. Discrepan: {discrepan or 'ninguna'}. Una base creada con "
        "`alembic upgrade head` tendría una columna en la que la aplicación no puede escribir."
    )


def test_la_migracion_que_corrige_es_condicional() -> None:
    """Alterar el tipo con `USING NULL` sin condición borraría los vectores buenos de una base
    que ya estaba bien — y regenerarlos cuesta GPU y horas."""
    correccion = MIGRACIONES / "e2b3c4d5f6a7_dimension_del_vector_1024.py"
    assert correccion.is_file(), "Falta la migración que corrige la dimensión"
    texto = correccion.read_text(encoding="utf-8")
    assert "IS DISTINCT FROM 'vector(1024)'" in texto, (
        "La migración tiene que comprobar la dimensión actual antes de alterar: en una base "
        "correcta no debe tocar nada."
    )
    assert "format_type" in texto, "La comprobación lee el tipo real de la columna."
