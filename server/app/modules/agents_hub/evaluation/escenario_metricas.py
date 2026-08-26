"""Las tres cosas que la fuente esperada estructurada permite calcular solas (HIB.G).

Vive en el repositorio y con tests, no en `_local/`, porque es **lógica** y no instrumental:
decidir si dos URL apuntan al mismo documento, o si un ancla apunta al artículo esperado, tiene
casos límite —la barra final, el ancla ausente, la versión idiomática— y cada uno de ellos, mal
resuelto, mueve una cifra sin dar ningún error. Lo que sí vive en `_local/` es lo que ejecuta el
lote contra el corpus real.

Las tres devuelven `None` cuando la pregunta no aplica, y eso es distinto de `False`. Un
escenario sin ancla esperada no «falla el ancla»: no la mide. Colapsar las dos cosas en un
booleano es la vía más corta para publicar un porcentaje sobre un denominador que nadie ha
mirado.
"""
from __future__ import annotations

from server.app.modules.agents_hub.evaluation.escenario_contrato import (
    Escenario,
    ExpectedSource,
)


def _normaliza_url(url: str | None) -> str:
    """Compara documentos sin que decida la barra final ni el esquema.

    El portal real sirve la misma sección con y sin barra y por http y https —lo documentó el
    bloque de curación—, así que comparar la cadena tal cual produce falsos negativos que se
    leen como fallos de recuperación.
    """
    if not url:
        return ""
    limpia = url.strip().lower()
    for prefijo in ("https://", "http://"):
        if limpia.startswith(prefijo):
            limpia = limpia[len(prefijo) :]
            break
    limpia, _, _ = limpia.partition("#")
    return limpia.rstrip("/")


def _normaliza_ancla(ancla: str | None) -> str:
    """`#art-4`, `art-4` y `ART-4` son el mismo artículo."""
    if not ancla:
        return ""
    return ancla.strip().lstrip("#").lower()


def _mismo_documento(esperada: ExpectedSource, recuperada: dict) -> bool:
    if esperada.document_id and recuperada.get("document_id"):
        if str(esperada.document_id) == str(recuperada["document_id"]):
            return True
    url_esperada = _normaliza_url(esperada.canonical_url)
    if url_esperada and url_esperada == _normaliza_url(recuperada.get("url")):
        return True
    return False


def fuentes_requeridas_recuperadas(
    escenario: Escenario, recuperadas: list[dict]
) -> tuple[int, int] | None:
    """Cuántas de las fuentes exigidas entraron en lo recuperado, y cuántas se exigían.

    `None` si el escenario no exige ninguna —los negativos—. El resultado es una fracción y no
    un booleano a propósito: en `varios_articulos` acertar una de dos no es acertar, pero
    tampoco es lo mismo que no acertar ninguna, y la diferencia es justo lo que dice si el
    fallo es de recuperación o de cobertura.
    """
    if not escenario.expected_sources or not escenario.expected_sources.required:
        return None
    exigidas = escenario.expected_sources.required
    encontradas = sum(
        1 for e in exigidas if any(_mismo_documento(e, r) for r in recuperadas)
    )
    return encontradas, len(exigidas)


def ancla_correcta(escenario: Escenario, recuperadas: list[dict]) -> bool | None:
    """Si la cita del documento esperado abre el artículo esperado.

    `None` cuando no hay ancla que comprobar: o el escenario no la declara, o el documento
    esperado no se recuperó —y entonces el fallo es de recuperación y atribuirlo al ancla
    sería contarlo dos veces—.
    """
    if not escenario.expected_sources:
        return None
    con_ancla = [e for e in escenario.expected_sources.required if e.anchor]
    if not con_ancla:
        return None

    comprobadas = []
    for esperada in con_ancla:
        iguales = [r for r in recuperadas if _mismo_documento(esperada, r)]
        if not iguales:
            continue
        esperado = _normaliza_ancla(esperada.anchor)
        comprobadas.append(
            any(_normaliza_ancla(r.get("url", "").rpartition("#")[2]) == esperado for r in iguales)
        )
    if not comprobadas:
        return None
    return all(comprobadas)


def rendicion_correcta(escenario: Escenario, se_rindio: bool) -> bool | None:
    """Si el asistente calló cuando debía y contestó cuando debía.

    `None` nunca: esto siempre se puede juzgar, y es la única de las tres que mide los dos ejes
    de la abstención a la vez. Para un negativo, callar es acertar; para una pregunta con
    respuesta en el corpus, callar es el fallo que el bloque RES vino a corregir.
    """
    return se_rindio if not escenario.answerable else not se_rindio


def resume(escenario: Escenario, recuperadas: list[dict], se_rindio: bool) -> dict:
    """Las tres métricas de un escenario, con la procedencia pegada al resultado.

    La procedencia viaja aquí y no sólo en el lote porque es donde se pierde: en cuanto alguien
    agrega estas filas, una anotada por el equipo pesa lo mismo que una de informador si nadie
    la distingue.
    """
    fuentes = fuentes_requeridas_recuperadas(escenario, recuperadas)
    return {
        "name": escenario.name,
        "kind": str(escenario.kind),
        "language": escenario.language,
        "provenance": str(escenario.provenance),
        "answerable": escenario.answerable,
        "fuentes_encontradas": None if fuentes is None else fuentes[0],
        "fuentes_exigidas": None if fuentes is None else fuentes[1],
        "todas_las_fuentes": None if fuentes is None else fuentes[0] == fuentes[1],
        "ancla_correcta": ancla_correcta(escenario, recuperadas),
        "rendicion_correcta": rendicion_correcta(escenario, se_rindio),
    }
