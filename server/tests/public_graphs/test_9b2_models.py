"""Tests de modelo ORM para campos de grafo público — TDD RED (9B.2).

Verifica las definiciones de columnas en HubChatbot y HubOrganizacion sin necesitar BD.
"""
import uuid

import pytest


def _get_col(table, name):
    return table.columns[name]


class TestHubChatbotPublicGraphFields:

    def test_chatbot_has_public_graph_profile_field(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        col = _get_col(HubChatbot.__table__, "public_graph_profile")
        assert col is not None
        assert col.default.arg == "PUBLIC_KB_RICH"

    def test_chatbot_has_retrieval_mode_default_rag(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        col = _get_col(HubChatbot.__table__, "retrieval_mode")
        assert col.default.arg == "RAG"

    def test_chatbot_has_language_mode_field(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        col = _get_col(HubChatbot.__table__, "language_mode")
        assert col.default.arg == "prefer"

    def test_chatbot_has_quality_threshold_field(self) -> None:
        """El default es **0,65**, y no el 0,6 que escribió 9B.2.

        Lo cambió **HIB.J**, y con él cambió el significado de la escala: la nota de la puerta era
        la **media** de los resultados, así que ensanchar `retrieval_top_k` la bajaba y el
        asistente contestaba menos; hoy lee la similitud coseno del mejor. Quien puso un umbral
        antes del 2026-08-25 lo puso con el otro significado.

        Este test no re-deriva el número: **registra la elección**. Un default de columna que
        cambia sin que nadie lo decida es una regresión silenciosa, y no hay otro sitio donde se
        vigile.
        """
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        col = _get_col(HubChatbot.__table__, "quality_threshold")
        assert col.default.arg == pytest.approx(0.65)

    def test_chatbot_has_min_retrieval_fields(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        cols = HubChatbot.__table__.columns
        assert "min_retrieval_results" in cols
        assert "min_retrieval_score" in cols
        assert cols["min_retrieval_results"].default.arg == 2
        # 0,0 y no el 0,25 de 9B.2: el mínimo de puntuación nace **desactivado**, y quien lo
        # quiera lo sube por chatbot. Con 0,25 por defecto, cada chatbot nuevo llegaba con un
        # filtro que su dueño no había pedido y que explicaba silencios que parecían del corpus.
        assert cols["min_retrieval_score"].default.arg == pytest.approx(0.0)

    def test_chatbot_has_reranker_enabled_field(self) -> None:
        """Nace **apagado**, y eso lo decidió una medición, no una preferencia.

        9B.2 lo puso a `True`. **HIB.A** lo apagó tras medirlo sobre cuatro ejes en el asistente
        de Normativa: no mejoraba la recuperación y añadía una llamada a Vertex por consulta.
        Encenderlo es una decisión por chatbot, con su medición detrás.
        """
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        col = _get_col(HubChatbot.__table__, "reranker_enabled")
        assert col.default.arg is False

    def test_chatbot_has_answer_template_field(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        col = _get_col(HubChatbot.__table__, "answer_template")
        assert col.default.arg == "generic"

    def test_two_chatbots_can_have_different_retrieval_mode(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        organizacion_id = uuid.uuid4()
        llm_id = uuid.uuid4()
        bot_a = HubChatbot(
            organizacion_id=organizacion_id, llm_config_id=llm_id,
            name="bot-a", system_prompt="a", retrieval_mode="RAG",
        )
        bot_b = HubChatbot(
            organizacion_id=organizacion_id, llm_config_id=llm_id,
            name="bot-b", system_prompt="b", retrieval_mode="MD_LONG_CONTEXT",
        )
        assert bot_a.retrieval_mode != bot_b.retrieval_mode


class TestHubOrganizacionPublicGraphDefaults:

    def test_org_has_default_retrieval_mode(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        col = _get_col(HubOrganizacion.__table__, "default_retrieval_mode")
        assert col.default.arg == "RAG"

    def test_org_has_default_public_graph_profile(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        col = _get_col(HubOrganizacion.__table__, "default_public_graph_profile")
        assert col.default.arg == "PUBLIC_KB_RICH"

    def test_org_has_all_default_graph_fields(self) -> None:
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        cols = HubOrganizacion.__table__.columns
        expected = {
            "default_public_graph_profile",
            "default_retrieval_mode",
            "default_language_mode",
            "default_quality_threshold",
            "default_min_retrieval_results",
            "default_min_retrieval_score",
            "default_reranker_enabled",
            "default_answer_template",
        }
        missing = expected - set(cols.keys())
        assert not missing, f"Faltan columnas en HubOrganizacion: {missing}"

    def test_org_has_no_allowed_profiles_restriction_field(self) -> None:
        """La organización no restringe qué perfiles puede usar un chatbot."""
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        cols = HubOrganizacion.__table__.columns
        assert "allowed_profiles" not in cols
        assert "allowed_retrieval_modes" not in cols
