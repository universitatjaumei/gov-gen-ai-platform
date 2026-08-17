"""Paquete de pipelines de extracción.

**Sin reexportaciones a propósito.** Este `__init__` reexportaba los seis pipelines, y eso
creaba un ciclo: `server.app.core.sandbox_client` importa `pipelines.contracts`, Python
inicializa antes el paquete, el paquete importaba `admin_script_pipeline` y ese vuelve a
`sandbox_client`, que está a medio cargar. Nadie usaba las reexportaciones —cada llamador
importa su submódulo— así que el ciclo no compraba nada. Importa el submódulo concreto.
"""
