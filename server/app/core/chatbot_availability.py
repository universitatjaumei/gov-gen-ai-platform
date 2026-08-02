"""Disponibilidad temporal y presupuesto acumulado de un chatbot (SEC.4.1). Deploy: edge.

Un chatbot de campaña —plazo de matrícula, convocatoria, periodo de alegaciones— tiene que
poder **caducar solo**. Hasta aquí la única palanca era que una persona se acordara de poner
`is_active = false` el día que tocaba, y esa persona se acuerda hasta que no se acuerda.

**El estado se calcula, no se guarda.** Tres razones, y las tres importan:

1. Un flag persistido se queda obsoleto en cuanto pasa la fecha, así que habría que
   inventar un job que lo refresque: infraestructura nueva para no calcular una resta.
2. El consumo acumulado es dato **operacional** (`HubUsageCounter`), y `HubChatbot` es
   configuración que se sincroniza cloud→edge. Guardar ahí el gasto rompería la frontera.
3. `is_active` seguiría significando dos cosas en un solo booleano: «el admin lo apagó» y
   «se le pasó el plazo». Son distintas, y quien mira el panel necesita distinguirlas.

**El 403 lleva el motivo y el mensaje que escribió el admin.** «El plazo de matrícula
terminó el 30 de septiembre» es una respuesta; «Forbidden» es un callejón.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status

from server.app.core.quotas import SUJETO_CHATBOT, VENTANA_TOTAL, consumo_de

DISPONIBLE = "available"
CADUCADO = "expired"
AUN_NO_ABIERTO = "not_yet_open"
PRESUPUESTO_AGOTADO = "budget_exhausted"


@dataclass(frozen=True)
class Disponibilidad:
    """Estado derivado. Se calcula al preguntarlo y no vive en ninguna columna."""

    state: str
    reason: str | None
    tokens_used: int
    total_token_budget: int | None

    @property
    def disponible(self) -> bool:
        return self.state == DISPONIBLE


def _ahora(momento: datetime | None) -> datetime:
    return momento or datetime.now(timezone.utc)


def _con_zona(fecha: datetime | None) -> datetime | None:
    """Una fecha sin zona se lee como UTC en vez de reventar la comparación.

    Postgres devuelve `timestamptz` con zona, pero un doble de test o una fila escrita por
    una herramienta antigua pueden traerla suelta, y ahí `<` lanza `TypeError`. Caerse al
    comprobar la vigencia dejaría el chatbot inaccesible por un detalle de tipos.
    """
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


async def calcular_disponibilidad(session, chatbot, momento: datetime | None = None):
    """El estado de este chatbot ahora mismo.

    El orden es el de la pregunta que se hace el ciudadano: ¿ya abrió?, ¿sigue abierto?,
    ¿queda presupuesto? El presupuesto va el último porque es el único que cuesta una
    consulta a la BD.
    """
    ahora = _ahora(momento)
    desde = _con_zona(getattr(chatbot, "valid_from", None))
    hasta = _con_zona(getattr(chatbot, "valid_until", None))
    presupuesto = getattr(chatbot, "total_token_budget", None)

    if desde is not None and ahora < desde:
        return Disponibilidad(AUN_NO_ABIERTO, AUN_NO_ABIERTO, 0, presupuesto)
    if hasta is not None and ahora > hasta:
        return Disponibilidad(CADUCADO, CADUCADO, 0, presupuesto)

    if not presupuesto:
        # `None` o `0`: sin techo acumulado. Mismo criterio que las cuotas de SEC.4, donde
        # `0` es «sin límite» y no «bloqueado».
        return Disponibilidad(DISPONIBLE, None, 0, presupuesto)

    # `window_key='total'` es el acumulado que SEC.4 ya escribe en cada interacción: aquí no
    # se cuenta nada nuevo, se lee lo que la contabilidad lleva sumando.
    gastados = await consumo_de(
        session, SUJETO_CHATBOT, str(getattr(chatbot, "id", "")), VENTANA_TOTAL
    )
    if gastados >= presupuesto:
        return Disponibilidad(PRESUPUESTO_AGOTADO, PRESUPUESTO_AGOTADO, gastados, presupuesto)

    return Disponibilidad(DISPONIBLE, None, gastados, presupuesto)


async def assert_chatbot_available(session, chatbot, momento: datetime | None = None) -> None:
    """403 con el motivo y el mensaje del admin si el chatbot no está abierto.

    Se invoca **después** de `assert_chatbot_access` y **antes** de `assert_within_quota`:
    primero «¿puedes hablar con este bot?», luego «¿está abierto?», luego «¿te queda cuota?».
    El orden no es estético — contarle a alguien que el plazo se cerró es contarle que el
    trámite existe, y eso solo se le dice a quien podría usarlo.
    """
    estado = await calcular_disponibilidad(session, chatbot, momento)
    if estado.disponible:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "CHATBOT_UNAVAILABLE",
            "reason": estado.reason,
            "message": getattr(chatbot, "unavailable_message", "") or None,
        },
    )
