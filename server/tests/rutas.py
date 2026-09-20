"""Las rutas que la aplicación sirve de verdad, recorriendo el árbol y no la primera capa.

**Por qué existe.** Once tests enumeraban `app.routes` como si fuera una lista plana, y lo era
hasta que `fastapi` pasó de 0.136 a 0.141: desde esa versión cada router incluido aparece como
**un solo objeto `_IncludedRouter`** que guarda los suyos dentro. Medido el 2026-09-20:
`app.routes` pasó de enumerarlas todas a tener **7 entradas**, mientras el esquema OpenAPI seguía
declarando **178 caminos**.

O sea que **la aplicación no cambió**: sirve exactamente lo mismo. Lo que se rompió fue la forma
de contarlas, y se comprobó antes de tocar nada preguntándole al esquema.

**Estaba anticipado y por escrito.** El cierre de DEP.3 dejó dicho que una subida de
`starlette`/`fastapi` podía dejar `app.routes` sin aplanar —nombrando incluso el
`_IncludedRouter`— y que afectaría a «los 14 tests que enumeran rutas». Entonces no ocurrió y no
se tocó nada. Ha ocurrido ahora, y fallaron **exactamente 14**.

**Por qué no se usa el esquema OpenAPI, que sería lo natural en un proyecto contract-first.**
Porque para lo que la mitad de estos tests comprueba **no sirve**: `fastapi` **inventa** un
`operationId` cuando el router no lo declara, así que en el esquema siempre hay uno y el test
pasaría sin comprobar nada. El `operation_id` explícito sólo se ve en el objeto de la ruta. El
esquema sí se usa, pero para **comprobar el propio recorrido**: si algún día deja de encontrar lo
que el contrato declara, `test_el_recorrido_ve_lo_que_el_contrato_declara` lo dice.
"""

from __future__ import annotations

from typing import Any, Iterator


def rutas_servidas(app: Any) -> Iterator[tuple[str, Any]]:
    """`(camino completo, ruta)` de todo lo que la aplicación sirve, a cualquier profundidad.

    El camino se compone con el prefijo de cada inclusión porque la ruta guardada dentro del
    router **no lo lleva**: `original_router` conserva `/opciones/lengua` y el `/api/v1/hub` lo
    pone el `include_router`. Sin componerlo, todo test que compare caminos completos fallaría
    dando la impresión de que la ruta no existe.
    """
    yield from _recorre(getattr(app, "routes", ()), set(), "")


def _recorre(rutas: Any, vistos: set[int], prefijo: str) -> Iterator[tuple[str, Any]]:
    for ruta in rutas or ():
        # Un router puede estar incluido dos veces —`cloud` y `edge` comparten alguno— y sin
        # esto saldría repetido; con una referencia circular, no acabaría.
        if id(ruta) in vistos:
            continue
        vistos.add(id(ruta))

        interno = getattr(ruta, "original_router", None)
        if interno is not None:
            contexto = getattr(ruta, "include_context", None)
            yield from _recorre(
                getattr(interno, "routes", ()),
                vistos,
                prefijo + (getattr(contexto, "prefix", "") or ""),
            )
        elif getattr(ruta, "routes", None):
            yield from _recorre(ruta.routes, vistos, prefijo)
        else:
            yield prefijo + getattr(ruta, "path", ""), ruta


def caminos(app: Any) -> set[str]:
    """Sólo los caminos, que es lo que la mayoría de estos tests quiere comprobar."""
    return {camino for camino, _ in rutas_servidas(app)}


def operaciones(app: Any) -> dict[str, str | None]:
    """`{camino: operation_id}`, con el identificador **declarado** y no el inventado.

    Un `operation_id` ausente no es cosmético: es lo que Orval convierte en el nombre del hook
    del frontend, y sin él genera uno a partir del método y la ruta que cambia al reordenar.
    """
    return {camino: getattr(r, "operation_id", None) for camino, r in rutas_servidas(app)}


def operaciones_por_metodo(app: Any) -> dict[tuple[str, str], str | None]:
    """`{(camino, MÉTODO): operation_id}`, para las rutas que sirven más de un verbo."""
    return {
        (camino, metodo): getattr(r, "operation_id", None)
        for camino, r in rutas_servidas(app)
        for metodo in getattr(r, "methods", set()) or ()
    }
