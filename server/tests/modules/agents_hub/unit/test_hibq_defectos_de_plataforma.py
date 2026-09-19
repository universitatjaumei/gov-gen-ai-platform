"""HIB.Q — un chatbot nuevo nace con lo que se ha medido.

Los cambios de HIB.J, HIB.B, HIB.C y HIB.I son código y los hereda cualquier chatbot, ya
creado o futuro. Pero tres parámetros son **configuración por chatbot**, y ahí un chatbot nuevo
no hereda lo que se puso a mano en Normativa: hereda el valor por omisión. Antes de este
prompt, un chatbot nuevo nacía con:

* `retrieval_top_k = 8`. Hasta HIB.J ese mando daba menos documentos de los que decía —el pool
  se encogía a `top_k` fragmentos y se agrupaba por documento—; ahora significa ocho documentos
  **enteros**, y con `parent_child` eso es casi el triple del contexto y del coste que se
  eligió para Normativa.
* `query_rewriting_enabled = False`. Desde HIB.C el widget **envía** los turnos previos, así
  que un chatbot nuevo recibiría el historial y no lo reescribiría: llega la fontanería y no la
  función, el seguimiento no funciona y no hay ningún error que lo delate.

**La trampa que decide cómo se arregla.** `_apply_layer` aplica sólo los valores **no nulos** de
cada capa, así que una columna NOT NULL del chatbot gana siempre al defecto de plataforma.
`retrieval_top_k` es NOT NULL con defecto 8: tocar sólo `_PLATFORM_DEFAULTS` no habría cambiado
nada para ningún chatbot, porque todas las filas traen un valor. Hay que mover **el defecto de
la columna**. `query_rewriting_enabled` sí es nullable, y ahí NULL significa heredar, así que su
sitio es la configuración de plataforma.

Lo que **no** cambia: `min_retrieval_results` se queda en 2 (el 1 de Normativa fue un apaño de
desarrollo con un corpus de un solo documento, no una decisión) y `reranker_enabled` ya estaba
en False, coherente con lo que midió HIB.A.

`quality_threshold` sí cambió, después de este prompt: HIB.Q lo dejó en el 0,6 que HIB.J había
elegido «por casualidad y no por diseño», y **HIB.R lo subió a 0,65** sobre la curva de las dos
columnas del lote de 48 —el único punto que declina dos negativos más sin perder ninguna
respuesta buena—. Este test se quedó afirmando el 0,6 y por eso llevaba días en rojo en CI.

Y los chatbots que ya existen **no se tocan**: un defecto de columna sólo actúa al insertar.
Decisión del usuario, 2026-08-27.

Deploy: edge
"""
from __future__ import annotations



class TestUnChatbotNuevoNaceConLoMedido:

    def test_should_default_the_width_to_three_documents(self):
        """Ocho documentos enteros con padre no es lo que se eligió midiendo."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        columna = HubChatbot.__table__.c["retrieval_top_k"]
        assert columna.default.arg == 3

    def test_should_default_to_rewriting_the_query(self):
        """Sin esto, el widget manda historial y el chatbot nuevo lo ignora en silencio.

        Se comprueba sobre la capa de plataforma y no construyendo `PublicGraphConfig()`:
        tiene campos obligatorios —`profile`, `retrieval_mode`, `language_mode`— y la cascada
        empieza en `_PLATFORM_DEFAULTS`, que es lo que de verdad hereda un chatbot con la
        columna nula.
        """
        from server.app.modules.agents_hub.agent.public_graphs.core import config_resolver

        assert config_resolver._PLATFORM_DEFAULTS.query_rewriting_enabled is True

    def test_should_keep_the_platform_defaults_that_were_already_right(self):
        from server.app.modules.agents_hub.agent.public_graphs.core import config_resolver

        por_defecto = config_resolver._PLATFORM_DEFAULTS
        # 0,65 desde HIB.R; ver el docstring del módulo.
        assert por_defecto.quality_threshold == 0.65
        assert por_defecto.reranker_enabled is False
        assert por_defecto.min_retrieval_results == 2

    def test_should_keep_the_width_above_the_minimum_of_results(self):
        """RAG.15: son dos decisiones distintas y confundirlas fue su defecto."""
        from server.app.modules.agents_hub.agent.public_graphs.core import config_resolver

        por_defecto = config_resolver._PLATFORM_DEFAULTS
        assert por_defecto.retrieval_top_k > por_defecto.min_retrieval_results

    def test_should_align_the_platform_default_with_the_column(self):
        """Dos números para la misma anchura divergirían en el primer cambio."""
        from server.app.modules.agents_hub.agent.public_graphs.core import config_resolver
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        assert (
            config_resolver._PLATFORM_DEFAULTS.retrieval_top_k
            == HubChatbot.__table__.c["retrieval_top_k"].default.arg
        )


class TestLaCascadaSigueRespetandoLoExplicito:

    def test_should_let_a_chatbot_override_the_platform_width(self):
        """El defecto es un punto de partida, no una imposición."""
        from dataclasses import replace

        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            _PLATFORM_DEFAULTS,
            _apply_layer,
        )

        resuelta = _apply_layer(_PLATFORM_DEFAULTS, {"retrieval_top_k": 6})
        assert resuelta.retrieval_top_k == 6
        # Y sin valor, se queda el de plataforma.
        assert _apply_layer(_PLATFORM_DEFAULTS, {"retrieval_top_k": None}).retrieval_top_k == 3
        assert replace(_PLATFORM_DEFAULTS).retrieval_top_k == 3

    def test_should_let_a_chatbot_turn_rewriting_off(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            _PLATFORM_DEFAULTS,
            _apply_layer,
        )

        assert (
            _apply_layer(_PLATFORM_DEFAULTS, {"query_rewriting_enabled": False}).
            query_rewriting_enabled
            is False
        )

    def test_should_not_change_the_chatbots_that_already_exist(self):
        """Un defecto de columna sólo actúa al INSERTAR: no hay `server_default`, así que
        ninguna fila existente se reescribe y no hace falta migración."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        columna = HubChatbot.__table__.c["retrieval_top_k"]
        assert columna.server_default is None
