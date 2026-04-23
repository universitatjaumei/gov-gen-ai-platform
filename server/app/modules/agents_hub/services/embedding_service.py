"""Servicio de embeddings vectoriales para búsqueda semántica."""
import os


class GoogleEmbeddingService:
    """Genera embeddings usando Google Generative AI (models/text-embedding-004)."""

    def __init__(self) -> None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        self._model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        )

    async def embed(self, text: str) -> list[float]:
        """Genera el embedding vectorial de un texto."""
        return await self._model.aembed_query(text)
