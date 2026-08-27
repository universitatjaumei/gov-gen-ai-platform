"""HIB.R — el umbral de calidad pasa a 0,65, elegido sobre la curva y no heredado.

**De dónde sale el 0,65.** Del lote de 48 escenarios de Normativa, calculando la curva de las
dos columnas sobre las notas guardadas —sin volver a generar nada, porque la puerta es
`nota >= umbral`—:

| umbral | declina bien (de 18) | contestables perdidos |
|---|---|---|
| 0,60 | 0 | 0 % |
| **0,65** | **2** | **0 %** |
| 0,70 | 4 | 7 % |
| 0,72 | 10 | 17 % |
| 0,75 | 16 | 50 % |

0,65 es el único punto que compra algo **sin pagar nada**. Y es todo lo que el umbral puede
comprar barato: los cinco casos de contratación que el asistente contesta y no debería puntúan
0,742-0,787, por encima de casi cualquier respuesta correcta, así que ningún umbral los alcanza
sin llevarse por delante la mitad de lo bueno. El resto del margen no está aquí — está en
comprobar el fundamento de la cita, que es el prompt siguiente.

**Por qué hay que mover el defecto de la COLUMNA y no sólo el de plataforma.** Es la trampa que
HIB.Q documentó: `_apply_layer` aplica sólo los valores no nulos de cada capa, y
`quality_threshold` es `nullable=False`. Un chatbot nuevo nace con el defecto de la columna, que
gana siempre al de plataforma. Cambiar sólo `_PLATFORM_DEFAULTS` no habría movido nada para
nadie, ni para los que ya existen ni para los que se creen.
"""
from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    _PLATFORM_DEFAULTS,
)
from server.app.modules.agents_hub.database.config_models import (
    HubChatbot,
    HubOrganizacion,
)


def _defecto(modelo, columna: str):
    return modelo.__table__.columns[columna].default.arg


class TestElUmbralElegidoLlegaAlChatbotNuevo:

    def test_should_default_the_quality_threshold_to_sixty_five(self):
        assert _defecto(HubChatbot, "quality_threshold") == 0.65

    def test_should_align_the_organization_default_with_the_chatbot_column(self):
        """La organización es la capa de en medio. Si se queda en 0,60, un chatbot que herede de
        ella acaba con el valor viejo aunque la columna diga otra cosa."""
        assert _defecto(HubOrganizacion, "default_quality_threshold") == 0.65

    def test_should_align_the_platform_default_too(self):
        """No porque haga falta para que funcione —la columna gana— sino para que no haya dos
        números para el mismo mando. Dos números es cómo se llega a no saber cuál rige."""
        assert _PLATFORM_DEFAULTS.quality_threshold == 0.65

    def test_should_not_carry_a_server_default_that_would_touch_existing_rows(self):
        """Un defecto de columna sólo actúa al insertar, y eso es lo que se quiere: los cuatro
        chatbots que ya existen tienen su umbral puesto a mano o medido, y el de Gerencia sigue
        en la escala vieja hasta que HIB.P lo elija. Un `server_default` con migración los
        cambiaría a todos de golpe."""
        assert HubChatbot.__table__.columns["quality_threshold"].server_default is None
        assert (
            HubOrganizacion.__table__.columns["default_quality_threshold"].server_default
            is None
        )
