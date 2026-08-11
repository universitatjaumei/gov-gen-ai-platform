"""Servicios de embeddings vectoriales para búsqueda semántica.

MOD.1: los dos servicios declaran `model_name` y `dimensions`. No es decorado — es lo que
permite grabar la procedencia con cada vector y que la guarda de `recalculate-corpus` pueda
saltar. Hasta MOD.1 esa guarda leía dos atributos que no existían, caía a los defaults y
comparaba `1024 != 1024`: estaba escrita y no podía dispararse nunca.

**La plataforma trabaja a 1024 dimensiones.** Es el único valor que sirve a la vez a BGE-M3
en edge (nativo) y a Google en cloud (rango flexible 128-3072), así que cambiar de proveedor
no obliga a migrar la columna `Vector(1024)` ni a reconstruir el índice HNSW. Detalle y
verificación en `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md`.
"""

import asyncio
import math
import os

DIMENSION_PLATAFORMA = 1024

# D.4.0: la pila de modelos locales (`torch`, `transformers`, `sentence-transformers`) es un
# extra de instalación. Un `ModuleNotFoundError: torch` en mitad de una ingesta no le dice a
# nadie qué instalar, así que se traduce a esto.
FALTA_EL_EXTRA = (
    "Este despliegue está configurado para usar {para}, pero la pila de modelos locales no "
    "está instalada. Instálala con:\n"
    "    uv sync --extra local-models\n"
    "O cambia la configuración para usar el proveedor por API, que es lo previsto en el "
    "despliegue estándar (ver docs/DECISION_MODELOS_EMBEDDING_RERANKER.md)."
)


def _l2_normalize(vector: list[float]) -> list[float]:
    norma = math.sqrt(sum(v * v for v in vector))
    return [v / norma for v in vector] if norma else vector


class LocalEmbeddingService:
    """Genera embeddings con BAAI/bge-m3 en local (CPU o GPU).

    El modelo se descarga desde HuggingFace Hub en la primera llamada (~1.1 GB).
    Las llamadas sucesivas reutilizan los pesos en memoria (singleton).
    Dimensión de salida: 1024 (dense, L2-normalizado por el propio modelo).
    """

    MODEL_NAME = "BAAI/bge-m3"

    def __init__(self) -> None:
        self._model = None

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def dimensions(self) -> int:
        return DIMENSION_PLATAFORMA

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as falta:
                raise RuntimeError(FALTA_EL_EXTRA.format(para="embeddings locales")) from falta
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    async def embed(self, text: str) -> list[float]:
        def _encode(t: str) -> list[float]:
            return self._get_model().encode(t, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode, text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Un `encode` para toda la lista (RAG.7).

        `SentenceTransformer.encode` acepta lista y la procesa por lotes internamente, así
        que una llamada por documento en vez de una por fragmento aprovecha la vectorización
        en vez de pagar el arranque de la inferencia N veces.
        """
        def _encode(ts: list[str]) -> list[list[float]]:
            return self._get_model().encode(ts, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode, texts)


class GoogleEmbeddingService:
    """Embeddings por API de Google, para el modo cloud.

    **Normaliza siempre**, y esa es la decisión que no se puede quitar: la API no normaliza
    las dimensiones distintas de 3072 —«you must manually normalize non-3072 dimensions»—, y
    mezclar vectores normalizados y sin normalizar en la misma columna rompe cualquier
    semántica de score absoluto, como el umbral de RAG.5. Normalizar aquí cuesta tres líneas
    y deja de depender de una nota al pie que cambia entre versiones del modelo.
    """

    MODEL_NAME = "gemini-embedding-001"

    def __init__(
        self,
        model_name: str | None = None,
        output_dimensionality: int = DIMENSION_PLATAFORMA,
        client=None,
    ) -> None:
        self._model_name = model_name or self.MODEL_NAME
        self._dimensions = output_dimensionality
        self._client = client if client is not None else self._build_client()

    def _build_client(self):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=f"models/{self._model_name}",
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            output_dimensionality=self._dimensions,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        return _l2_normalize(await self._client.aembed_query(text))


_local_service: LocalEmbeddingService | None = None


def get_embedding_service() -> LocalEmbeddingService:
    """Singleton del servicio local — carga el modelo solo en la primera llamada.

    Sigue devolviendo el local a propósito: la selección por configuración es MOD.2. Cambiar
    esto aquí, sin la cascada y sin el guardarraíl de espacio vectorial, sería justo el
    interruptor silencioso que MOD.1 viene a impedir.
    """
    global _local_service
    if _local_service is None:
        _local_service = LocalEmbeddingService()
    return _local_service
