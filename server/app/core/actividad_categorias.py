"""Punto de partida del catálogo de categorías de datos del registro de actividad IA (REG.8).

Deploy: cloud — es configuración institucional y vive en `hub_vocabulary_terms`, que se
sincroniza cloud→edge.

**Por qué existe una semilla y no un catálogo vacío.** `categorias_datos` es vocabulario abierto:
el `POST` acepta cualquier código, porque rechazar uno no catalogado convertiría «esta categoría
todavía no está dada de alta» en «este uso de IA no queda registrado». Pero un catálogo vacío no
lo rellena nadie: el primer integrador inventa sus códigos, el segundo inventa otros, y el
registro deja de poder agregarse — que es justamente para lo que existe en una auditoría.

Con un punto de partida convencional, las herramientas convergen desde el primer día y renombrar
después es una fila nueva con `substituit_per_codi`, no una reclasificación a mano.

**Estas etiquetas están pendientes de validación** por quien lleve el registro de actividades de
tratamiento de la organización. Es la misma postura que el vocabulario del corpus con Secretaría
General, y la razón de que esto viva en la misma tabla: retirar, renombrar y fusionar sin
migración ni despliegue.

Los códigos siguen las categorías con las que se escribe habitualmente un registro de actividades
del art. 30 del RGPD, con `datos_de_categoria_especial` para lo del art. 9 cuando no haga falta
más detalle. **No son un `Enum`**: son dato (I4), y esta tupla es su semilla, no su definición.
"""
from __future__ import annotations

#: Categorías iniciales, en el orden en que se ofrecen. `(codigo, nombre)`.
CATEGORIAS_INICIALES: tuple[tuple[str, str], ...] = (
    ("datos_identificativos", "Datos identificativos"),
    ("datos_de_contacto", "Datos de contacto"),
    ("caracteristicas_personales", "Características personales"),
    ("datos_academicos_y_profesionales", "Datos académicos y profesionales"),
    ("datos_economicos_y_financieros", "Datos económicos y financieros"),
    ("datos_de_trafico_y_conexion", "Datos de tráfico y de conexión"),
    # Art. 9 del RGPD agrupado, y a propósito: quien registra desde una herramienta externa no
    # tiene por qué saber distinguir el subtipo, y forzarle a elegir mal es peor que la categoría
    # gruesa. Si una organización necesita el detalle, da de alta sus términos.
    ("datos_de_categoria_especial", "Datos de categoría especial (art. 9 RGPD)"),
    # Hace falta poder decirlo: sin este código, una lista vacía es ambigua entre «no hubo datos
    # personales» y «no lo declaré», y en una auditoría son dos cosas muy distintas.
    ("sin_datos_personales", "Sin datos personales"),
)
