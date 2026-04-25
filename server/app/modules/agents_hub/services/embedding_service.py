"""Servicio de embeddings vectoriales para búsqueda semántica."""

import asyncio
import os


class LocalEmbeddingService:
    """Genera embeddings con BAAI/bge-m3 en local (CPU o GPU).

    El modelo se descarga desde HuggingFace Hub en la primera llamada (~1.1 GB).
    Las llamadas sucesivas reutilizan los pesos en memoria (singleton).
    Dimensión de salida: 1024 (dense, L2-normalizado).
    """

    MODEL_NAME = "BAAI/bge-m3"

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    async def embed(self, text: str) -> list[float]:
        def _encode(t: str) -> list[float]:
            return self._get_model().encode(t, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode, text)


class GoogleEmbeddingService:
    """Genera embeddings usando Google Generative AI (models/text-embedding-004).

    Para uso en modo cloud cuando no se dispone de edge local.
    Dimensión de salida: 768.
    """

    def __init__(self) -> None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        self._model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        )

    async def embed(self, text: str) -> list[float]:
        return await self._model.aembed_query(text)


_local_service: LocalEmbeddingService | None = None


def get_embedding_service() -> LocalEmbeddingService:
    """Singleton del servicio local — carga el modelo solo en la primera llamada."""
    global _local_service
    if _local_service is None:
        _local_service = LocalEmbeddingService()
    return _local_service
