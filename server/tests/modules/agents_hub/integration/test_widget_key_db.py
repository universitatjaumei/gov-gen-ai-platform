"""Tests SEC.8.5 (con BD) — la credencial de sitio se resuelve y se revoca.

Viven aparte de tests/api/test_widget_key.py porque necesitan la fixture db_session, que
es de este directorio.
"""
from __future__ import annotations




class TestLaCredencialContraLaBaseDeDatos:
    async def test_should_resolve_an_active_key_to_its_chatbot(self, db_session):
        from server.app.core.auth.widget_key import (
            crear_widget_key,
            resolver_widget_key,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        _, chatbot = await _organizacion_y_chatbot(db_session)
        await db_session.commit()

        plano, fila = await crear_widget_key(
            db_session, chatbot_id=chatbot.id, name="Portal", created_by="admin-1"
        )
        await db_session.commit()

        resuelto = await resolver_widget_key(db_session, plano)
        assert resuelto is not None
        assert resuelto.chatbot_id == chatbot.id
        assert fila.key_hash != plano

    async def test_should_not_resolve_a_revoked_key(self, db_session):
        from datetime import datetime, timezone

        from server.app.core.auth.widget_key import (
            crear_widget_key,
            resolver_widget_key,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        _, chatbot = await _organizacion_y_chatbot(db_session)
        await db_session.commit()

        plano, fila = await crear_widget_key(
            db_session, chatbot_id=chatbot.id, name="Portal", created_by="admin-1"
        )
        fila.revoked_at = datetime.now(timezone.utc)
        await db_session.commit()

        assert await resolver_widget_key(db_session, plano) is None

    async def test_should_not_resolve_an_unknown_key(self, db_session):
        from server.app.core.auth.widget_key import resolver_widget_key

        assert await resolver_widget_key(db_session, "no-existe") is None
