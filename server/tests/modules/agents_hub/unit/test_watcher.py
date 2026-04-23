"""Tests para el watcher de ingestión."""
import uuid
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestIngestionWatcher:

    @pytest.mark.asyncio
    async def test_process_source_creates_chunks(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        with patch('server.app.modules.agents_hub.ingestion.watcher.DoclingProcessor') as mock_docling:
            mock_docling.return_value.process.return_value = "# Test\n\nContent"

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value=Mock(
                    scalar_one_or_none=Mock(return_value=None),
                    scalars=Mock(return_value=[]),
                )
            )

            watcher = IngestionWatcher(
                session=mock_session,
                embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1] * 1536)),
            )

            chunks = await watcher.process_source(
                source_url="https://example.com",
                chatbot_id=uuid.uuid4(),
            )

            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_process_skips_unchanged_content(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = Mock(
            content_hash="existing_hash"
        )

        watcher = IngestionWatcher(
            session=mock_session,
            embedding_service=AsyncMock(),
        )

        # El hash del nuevo contenido coincide con el existente
        with patch('server.app.modules.agents_hub.ingestion.watcher.hash_content', return_value="existing_hash"):
            with patch('server.app.modules.agents_hub.ingestion.watcher.DoclingProcessor') as mock_docling:
                mock_docling.return_value.process.return_value = "Content"

                result = await watcher.process_source(
                    source_url="https://example.com",
                    chatbot_id=uuid.uuid4(),
                )
                # Debe devolver lista vacía si no hay cambios
                assert len(result) == 0
