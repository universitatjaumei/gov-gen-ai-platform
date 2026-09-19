"""Tests para el chunker de markdown."""


class TestMarkdownChunker:

    def test_split_by_headers(self) -> None:
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        markdown = '''# Título Principal

Este es el contenido del título principal.

## Sección 1

Contenido de la sección 1.

## Sección 2

Contenido de la sección 2.
'''
        chunker = MarkdownChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.split(markdown)

        assert len(chunks) >= 2
        assert any("Sección 1" in c.content for c in chunks)

    def test_preserves_metadata(self) -> None:
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        markdown = '''# Título

Contenido bajo el título.
'''
        chunker = MarkdownChunker()
        chunks = chunker.split(markdown, metadata={"source": "test.md"})

        assert chunks[0].metadata["source"] == "test.md"

    def test_respects_chunk_size(self) -> None:
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        long_content = "# Título\n\n" + "Palabra " * 1000
        chunker = MarkdownChunker(chunk_size=200, chunk_overlap=20)
        chunks = chunker.split(long_content)

        for chunk in chunks:
            assert len(chunk.content) <= 300  # Con margen
