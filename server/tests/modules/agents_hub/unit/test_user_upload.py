"""Tests para la ingestiÃ³n de documentos de usuario (contexto temporal)."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestUserUploadIngestion:

    @pytest.mark.asyncio
    async def test_user_upload_is_not_visible_to_other_users(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        chatbot_id = uuid.uuid4()

        with patch('server.app.modules.agents_hub.ingestion.watcher.DoclingProcessor') as mock_docling:
            mock_docling.return_value.process.return_value = "# Doc A\n\nContenido privado."

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value=Mock(
                    scalar_one_or_none=Mock(return_value=None),
                    scalars=Mock(return_value=[]),
                )
            )

            watcher = IngestionWatcher(
                session=mock_session,
                embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024)),
            )

            chunks = await watcher.process_user_upload(
                source_url="https://example.com/doc_a.pdf",
                chatbot_id=chatbot_id,
                owner_id=user_a,
            )

        # Los chunks creados pertenecen a user_a y son temporales
        assert all(c.owner_id == user_a for c in chunks)
        assert all(c.is_temporary for c in chunks)

        # user_b no es owner de ninguno
        assert not any(c.owner_id == user_b for c in chunks)

    @pytest.mark.asyncio
    async def test_temporary_chunks_cleanup(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import cleanup_temporary_chunks

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        old_chunk = Mock()
        old_chunk.is_temporary = True
        old_chunk.created_at = cutoff - timedelta(hours=1)  # mÃ¡s de 24h

        recent_chunk = Mock()
        recent_chunk.is_temporary = True
        recent_chunk.created_at = cutoff + timedelta(hours=1)  # menos de 24h

        non_temp_chunk = Mock()
        non_temp_chunk.is_temporary = False
        non_temp_chunk.created_at = cutoff - timedelta(hours=1)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=[old_chunk, recent_chunk, non_temp_chunk]))
        )

        deleted = await cleanup_temporary_chunks(mock_session, ttl_hours=24)

        # Solo el chunk antiguo y temporal debe eliminarse
        assert deleted == 1
        mock_session.delete.assert_called_once_with(old_chunk)
