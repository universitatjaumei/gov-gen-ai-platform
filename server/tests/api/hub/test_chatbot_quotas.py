"""SEC.4 — los techos de consumo se pueden fijar sin abrir la base de datos.

`core/quotas.py` los aplica desde SEC.4 y las columnas existen desde entonces, pero **no
los exponía ni la API ni la interfaz**: la única forma de ponerlos era un `UPDATE` a mano,
así que en la práctica se quedaban en NULL. Para un chatbot `public_anon` eso significa
**sin límite por IP**, que es justo el sujeto para el que se construyó la contabilidad.

Se descubrió al montar el piloto (PIL.5) y se cierra aquí.

Semántica, que es la de SEC.4 y no se toca: **NULL = heredar de la organización**, **0 = sin
límite**. `anon_ip_daily_token_quota` no hereda: un chatbot público y uno interno no
comparten criterio sobre lo que es razonable para un anónimo.
"""
from __future__ import annotations

import uuid

from server.app.routers.hub_chatbots_router import (
    ChatbotCreate,
    ChatbotRead,
    ChatbotUpdate,
)

CUOTAS = (
    "user_daily_token_quota",
    "chatbot_daily_token_quota",
    "anon_ip_daily_token_quota",
)


class TestLasCuotasTienenSuperficie:

    def test_should_accept_the_three_quotas_when_creating(self):
        cuerpo = ChatbotCreate(
            name="Público",
            organizacion_id=uuid.uuid4(),
            llm_config_id=uuid.uuid4(),
            system_prompt="…",
            user_daily_token_quota=10_000,
            chatbot_daily_token_quota=500_000,
            anon_ip_daily_token_quota=50_000,
        )

        assert cuerpo.anon_ip_daily_token_quota == 50_000

    def test_should_expose_the_three_quotas_when_reading(self):
        for campo in CUOTAS:
            assert campo in ChatbotRead.model_fields, campo

    def test_should_accept_the_three_quotas_when_updating(self):
        for campo in CUOTAS:
            assert campo in ChatbotUpdate.model_fields, campo

    def test_should_default_to_inheriting(self):
        """Sin decir nada, NULL: heredar. No se inventa un techo por defecto."""
        cuerpo = ChatbotCreate(
            name="Público",
            organizacion_id=uuid.uuid4(),
            llm_config_id=uuid.uuid4(),
            system_prompt="…",
        )

        assert all(getattr(cuerpo, campo) is None for campo in CUOTAS)

    def test_should_distinguish_clearing_a_quota_from_not_touching_it(self):
        """`null` explícito significa «vuelve a heredar», y hay que poder decirlo.

        Es el mismo agujero que tenía `valid_until` antes de SEC.4.1: sin esto, un techo
        puesto una vez no se puede quitar por la API.
        """
        sin_tocar = ChatbotUpdate(name="otro nombre")
        limpiando = ChatbotUpdate(anon_ip_daily_token_quota=None)

        assert "anon_ip_daily_token_quota" not in sin_tocar.model_fields_set
        assert "anon_ip_daily_token_quota" in limpiando.model_fields_set

    def test_should_keep_zero_as_a_meaningful_value(self):
        """0 es «sin límite», no «bloqueado»: mismo criterio que `total_token_budget`."""
        cuerpo = ChatbotUpdate(chatbot_daily_token_quota=0)

        assert cuerpo.chatbot_daily_token_quota == 0
        assert "chatbot_daily_token_quota" in cuerpo.model_fields_set
