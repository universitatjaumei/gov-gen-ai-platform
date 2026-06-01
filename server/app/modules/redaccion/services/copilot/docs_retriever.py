"""Retriever de documentación interna: indexa Markdown, embebe con BGE-M3, retrieve filtrado por módulo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .models import CopilotModule, SourceRef


@dataclass
class IndexedChunk:
    text: str
    source_path: str
    module: CopilotModule
    chunk_idx: int
    embedding: list[float] = field(default_factory=list)

    def to_source_ref(self) -> SourceRef:
        excerpt = self.text.strip().replace("\n", " ")
        if len(excerpt) > 200:
            excerpt = excerpt[:197] + "…"
        return SourceRef(
            path=self.source_path,
            chunk_idx=self.chunk_idx,
            excerpt=excerpt,
            module=self.module,
        )


class DocsRetriever:
    """Indexa Markdown bajo `docs_dir`, embebe chunks y permite retrieve filtrado por módulo.

    Estado en memoria: pensado para docs estables (decenas de archivos). Si crece,
    migrar a pgvector reutilizando `HubDocumentChunk` con namespace 'copilot_docs'.
    """

    def __init__(
        self,
        embedding_service: Any,
        docs_dir: Path | None = None,
        chunk_size: int = 1200,
    ) -> None:
        self._embedding = embedding_service
        self._docs_dir = docs_dir or Path("docs")
        self._chunk_size = chunk_size
        self._chunks: list[IndexedChunk] = []

    @property
    def chunks(self) -> list[IndexedChunk]:
        return list(self._chunks)

    async def index(self) -> None:
        """Recorre `docs_dir` recursivo, chunkea cada `.md` y embebe cada fragmento."""
        self._chunks.clear()
        if not self._docs_dir.exists():
            return
        for md_path in sorted(self._docs_dir.rglob("*.md")):
            module = self._infer_module(md_path)
            for idx, chunk in enumerate(self._chunk_markdown(md_path)):
                if not chunk.strip():
                    continue
                embedding = await self._embedding.embed(chunk)
                self._chunks.append(
                    IndexedChunk(
                        text=chunk,
                        source_path=str(md_path),
                        module=module,
                        chunk_idx=idx,
                        embedding=embedding,
                    )
                )

    async def retrieve(
        self,
        query: str,
        module: CopilotModule | None = None,
        top_k: int = 4,
    ) -> list[IndexedChunk]:
        """Retrieve por similitud coseno. Si `module` se da, filtra antes de puntuar."""
        if not self._chunks:
            return []
        query_emb = await self._embedding.embed(query)
        candidates = [c for c in self._chunks if module is None or c.module == module]
        scored = [(_cosine(query_emb, c.embedding), c) for c in candidates]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _score, chunk in scored[:top_k]]

    def _chunk_markdown(self, path: Path) -> Iterator[str]:
        """Particiona el archivo por párrafos (doble newline) acumulando hasta `chunk_size`."""
        text = path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        buffer: list[str] = []
        size = 0
        for para in paragraphs:
            if size + len(para) > self._chunk_size and buffer:
                yield "\n\n".join(buffer)
                buffer = [para]
                size = len(para)
            else:
                buffer.append(para)
                size += len(para)
        if buffer:
            yield "\n\n".join(buffer)

    @staticmethod
    def _infer_module(path: Path) -> CopilotModule:
        haystack = str(path).lower()
        if "redaccion" in haystack:
            return "redaccion"
        if "chatbot" in haystack:
            return "chatbots"
        return "general"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
