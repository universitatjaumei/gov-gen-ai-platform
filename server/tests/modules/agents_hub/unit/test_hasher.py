"""Tests para el hasher de documentos."""
import pytest


class TestDocumentHasher:

    def test_hash_content_returns_sha256(self) -> None:
        from server.app.modules.agents_hub.ingestion.hasher import hash_content

        content = "Este es un documento de prueba."
        result = hash_content(content)

        assert len(result) == 64  # SHA-256 hex
        assert result.isalnum()

    def test_same_content_same_hash(self) -> None:
        from server.app.modules.agents_hub.ingestion.hasher import hash_content

        content = "Contenido idéntico"
        hash1 = hash_content(content)
        hash2 = hash_content(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        from server.app.modules.agents_hub.ingestion.hasher import hash_content

        hash1 = hash_content("Contenido A")
        hash2 = hash_content("Contenido B")

        assert hash1 != hash2

    def test_hash_file_returns_hash(self) -> None:
        from server.app.modules.agents_hub.ingestion.hasher import hash_file
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Contenido del archivo")
            temp_path = f.name

        result = hash_file(Path(temp_path))
        assert len(result) == 64

        Path(temp_path).unlink()
