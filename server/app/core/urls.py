"""Comparar URL del corpus sin que decida la barra final ni el esquema.

Deploy: shared

**Por qué es una función y no un `==`.** El portal real sirve la misma sección con y sin barra
final y por `http` y por `https` —lo documentó el bloque de curación, que se encontró la misma
página contada dos veces por eso—, y una cita al mismo documento puede traer ancla o no traerla.
Comparar la cadena tal cual produce falsos negativos que se leen como fallos de recuperación, o
como un 404 en un documento que existe.

**Vivía privada en `evaluation/escenario_metricas.py`** como `_normaliza_url`, y ahí la usaba el
emparejador de citas del dorado. VAS.2 necesita exactamente la misma comparación para resolver
`?url=` al documento del corpus, y la regla del bloque es clara: si el servicio necesita algo que
la función no da —aquí, simplemente ser pública—, **se cambia la función y quien la usaba la
hereda**, nunca una copia. Aquel módulo la importa de aquí.

Dos normalizadores de URL divergen en el primer caso raro que aparezca, y entonces el emparejador
del dorado y la verificación de vigencia dejan de hablar del mismo documento sin que nada avise.
"""
from __future__ import annotations


def normalizar_url(url: str | None) -> str:
    """La forma canónica para comparar: sin esquema, sin ancla, sin barra final, en minúsculas.

    No sirve para navegar —lo que devuelve no es una URL— sino sólo para decidir si dos cadenas
    hablan del mismo documento.
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
