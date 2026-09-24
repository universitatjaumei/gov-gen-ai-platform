"""Métricas de recuperación (RAG.1). Deploy: edge.

**Funciones puras sobre listas de identificadores: sin LLM, sin red y sin BD.** Es lo que
permite que el gate de CI corra en segundos y se ejecute en cada cambio del retriever.

Desde el 2026-09-24 esto es **toda** la medición automática de calidad que hay, junto con las
tres comprobaciones de cita de `escenario_metricas.py`. Aquí hubo también un `rag_metrics.py`
con métricas de RAGAS —fidelidad y relevancia, con LLM— y se retiró porque sus dos funciones no
tenían ningún llamador fuera de los tests. Lo que mide este fichero es la **recuperación**: si
salió lo que tenía que salir. La calidad de la *respuesta* no se mide sola, y su sitio es la
revisión humana.

Los identificadores pueden ser URLs canónicas o ids de documento: a las métricas les da
igual, siempre que el dorado y lo recuperado usen el mismo eje.
"""
from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int = 5) -> float:
    """Fracción de los esperados que aparecen en los primeros `k` recuperados.

    Devuelve 0.0 cuando no hay esperados: una consulta sin objetivo no puede puntuar 1,
    porque falsearía la media del informe al alza.
    """
    objetivos = set(expected)
    if not objetivos:
        return 0.0
    encontrados = objetivos & set(retrieved[:k])
    return len(encontrados) / len(objetivos)


def mrr(retrieved: Sequence[str], expected: Sequence[str]) -> float:
    """Recíproco del rango de la PRIMERA coincidencia (0.0 si no hay ninguna).

    Mide lo arriba que llega el primer acierto, que es lo que decide si el contexto
    inyectado lo contiene cuando el presupuesto recorta.
    """
    objetivos = set(expected)
    if not objetivos:
        return 0.0
    for posicion, identificador in enumerate(retrieved, start=1):
        if identificador in objetivos:
            return 1.0 / posicion
    return 0.0


def promedio(valores: Sequence[float]) -> float:
    """Media, o 0.0 sobre una secuencia vacía (no None: el informe siempre tiene cifras)."""
    return sum(valores) / len(valores) if valores else 0.0
