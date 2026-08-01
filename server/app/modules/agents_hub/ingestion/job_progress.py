"""Seguimiento por etapas de un job de ingesta (RAG.12). Deploy: edge.

`status` solo distingue pending/running/completed/failed, y una conversión de Docling sobre
un PDF largo tarda minutos: desde fuera, un job trabajando y un job colgado son
indistinguibles. Lo que falta no es más log — es estado consultable.

**El acumulador vive en memoria, y eso no es un detalle**: cuando un job revienta, el
manejador de errores hace `rollback()`, así que unas estadísticas escritas en la fila
conforme se generan se perderían justo en el caso en que más falta hacen. Al vivir en un
objeto de Python sobreviven al rollback y se escriben después, junto al estado `failed`.

**El aviso es por etapa o por lote, nunca por fragmento.** Un corpus de 3.000 documentos con
un `UPDATE` por chunk convierte la barra de progreso en la parte cara de la ingesta.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, Callable

# (actual, total_o_None, mensaje)
ProgressCallback = Callable[[int, int | None, str], None]


class SeguimientoDeJob:
    """Cronómetro por etapa + contador de progreso. Sin callback, no hace nada visible."""

    def __init__(self, callback: ProgressCallback | None = None) -> None:
        self._callback = callback
        self.actual = 0
        self.total: int | None = None
        self.mensaje = ""
        self.stage_ms: dict[str, int] = {}
        self.failed_stage: str | None = None
        self.n_chunks = 0
        self.total_chars = 0
        self.n_batches = 0
        self.embedding_model: str | None = None

    def avisar(self, mensaje: str, actual: int | None = None) -> None:
        """Informa del estado. Es el único punto por el que sale información hacia fuera.

        **`actual` se cuenta en fragmentos, no en etapas**, y el mensaje dice en qué etapa
        va. Contar etapas produciría fracciones como `4/3` —el numerador en pasos y el
        denominador en fragmentos—, que es peor que no informar. Antes de trocear no hay
        numerador ni denominador que valgan: se queda en 0 y `total` en None.
        """
        if actual is not None:
            self.actual = actual
        self.mensaje = mensaje
        if self._callback is not None:
            self._callback(self.actual, self.total, mensaje)

    @asynccontextmanager
    async def etapa(self, nombre: str, detalle: str = "", actual: int | None = None):
        """Mide la etapa y deja `failed_stage` puesto si revienta dentro.

        Que el nombre quede marcado ANTES de entrar y solo se limpie al salir bien es lo que
        permite decir «falló embebiendo» en vez de «falló».
        """
        self.failed_stage = nombre
        self.avisar(f"{nombre}: {detalle}" if detalle else nombre, actual)
        inicio = time.perf_counter()
        try:
            yield self
        finally:
            self.stage_ms[nombre] = int((time.perf_counter() - inicio) * 1000)
        self.failed_stage = None

    def resumen(self) -> dict[str, Any]:
        """Lo que se guarda en `processing_stats`, completo o a medias."""
        datos: dict[str, Any] = {
            "n_chunks": self.n_chunks,
            "total_chars": self.total_chars,
            "n_batches": self.n_batches,
            "embedding_model": self.embedding_model,
            "stage_ms": dict(self.stage_ms),
        }
        if self.failed_stage:
            datos["failed_stage"] = self.failed_stage
        return datos
