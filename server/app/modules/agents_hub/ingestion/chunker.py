"""Chunker para documentos Markdown."""
from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """Representa un chunk de documento."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MarkdownChunker:
    """Divide documentos Markdown en chunks semánticos."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.headers_to_split = [
            ("#", "header_1"),
            ("##", "header_2"),
            ("###", "header_3"),
        ]

        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split,
            strip_headers=False,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, content: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Divide el contenido en chunks.

        Args:
            content: Contenido Markdown
            metadata: Metadatos adicionales

        Returns:
            Lista de chunks
        """
        base_metadata = metadata or {}

        md_docs = self.md_splitter.split_text(content)

        chunks = []
        for doc in md_docs:
            doc_content = doc.page_content
            doc_metadata = {**base_metadata, **doc.metadata}

            if len(doc_content) > self.chunk_size:
                sub_docs = self.text_splitter.split_text(doc_content)
                for i, sub_content in enumerate(sub_docs):
                    chunks.append(Chunk(
                        content=sub_content,
                        metadata={**doc_metadata, "chunk_index": i},
                    ))
            else:
                chunks.append(Chunk(content=doc_content, metadata=doc_metadata))

        return chunks
