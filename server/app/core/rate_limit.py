"""Limitación de peticiones por ventana (SEC.4, Parte 1). Deploy: shared.

Dos cosas distintas que la gente confunde: **esto cuenta peticiones**, las cuotas de
`quotas.py` cuentan tokens. El limitador frena la fuerza bruta contra el login y el martilleo
del chat; la cuota controla el gasto. Una petición puede costar mil veces más que otra, así
que ninguna de las dos sustituye a la otra.

**Ventana deslizante en memoria del proceso, y no Redis.** Es una decisión con su límite
escrito: con varias instancias detrás de un balanceador, cada una cuenta lo suyo, así que el
límite efectivo se multiplica por el número de instancias. Para lo que este limitador
defiende —fuerza bruta contra un login que ya exige contraseña desde SEC.1— eso sigue siendo
tres órdenes de magnitud menos que sin límite, y no arrastra una dependencia de
infraestructura al despliegue edge, donde a menudo hay **una** instancia y no hay Redis.
Cuando el despliegue en Cloud Run escale de verdad, el reemplazo es este mismo módulo con
otro almacén detrás: la superficie es `permitir()` y nada más.

La memoria está acotada: las claves caducan solas al quedarse sin marcas dentro de la ventana
y se recogen al consultarlas.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

# Por defecto conservador en el login —fuerza bruta— y holgado en el chat, donde una persona
# haciendo preguntas seguidas es un uso normal y no un ataque.
LIMITE_LOGIN_POR_DEFECTO = "10/minute"
LIMITE_CHAT_POR_DEFECTO = "30/minute"

_UNIDADES = {"second": 1, "minute": 60, "hour": 3600, "day": 86_400}


def _parsear(regla: str) -> tuple[int, int]:
    """`'10/minute'` → `(10, 60)`. Una regla ilegible no se interpreta: se levanta."""
    try:
        veces, unidad = regla.split("/")
        return int(veces), _UNIDADES[unidad.strip().lower()]
    except (ValueError, KeyError) as fallo:
        raise RuntimeError(
            f"Regla de límite inválida: {regla!r}. Formato: '<n>/<second|minute|hour|day>'"
        ) from fallo


class LimitadorEnMemoria:
    """Ventana deslizante por clave. Seguro entre hilos; no entre procesos (ver módulo)."""

    def __init__(self) -> None:
        self._marcas: dict[str, deque[float]] = defaultdict(deque)
        self._cerrojo = Lock()

    def permitir(self, clave: str, regla: str, ahora: float | None = None) -> tuple[bool, int]:
        """`(permitida, segundos_hasta_que_se_libere)`."""
        veces, ventana = _parsear(regla)
        instante = ahora if ahora is not None else time.monotonic()

        with self._cerrojo:
            marcas = self._marcas[clave]
            while marcas and instante - marcas[0] >= ventana:
                marcas.popleft()

            if len(marcas) >= veces:
                return False, max(1, int(ventana - (instante - marcas[0])))

            marcas.append(instante)
            if not marcas:
                del self._marcas[clave]
            return True, 0

    def reiniciar(self) -> None:
        """Solo para tests: un limitador con memoria entre tests da falsos rojos."""
        with self._cerrojo:
            self._marcas.clear()


limitador = LimitadorEnMemoria()


def ip_de(request: Request) -> str:
    """La IP del cliente, respetando `X-Forwarded-For` cuando hay proxy delante.

    Se toma **el primer** valor de la cadena, que es el cliente original. Es falsificable si
    la aplicación estuviera expuesta directamente a internet, pero en ese caso no habría
    cabecera; detrás de Cloud Run o de un balanceador, la pone la infraestructura.
    """
    reenviada = request.headers.get("X-Forwarded-For")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return getattr(getattr(request, "client", None), "host", None) or "desconocida"


def _regla(variable: str, por_defecto: str) -> str:
    return os.getenv(variable, por_defecto)


def limitar(request: Request, *, ambito: str, clave: str, regla: str) -> None:
    """429 si esta clave ha gastado su cupo en la ventana."""
    permitida, espera = limitador.permitir(f"{ambito}:{clave}", regla)
    if not permitida:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "scope": ambito, "limit": regla},
            headers={"Retry-After": str(espera)},
        )


def limitar_login(request: Request) -> None:
    """Por IP: en el login todavía no se sabe quién llama, y esa es la gracia del ataque."""
    limitar(
        request,
        ambito="login",
        clave=ip_de(request),
        regla=_regla("RATE_LIMIT_LOGIN", LIMITE_LOGIN_POR_DEFECTO),
    )


def limitar_chat(request: Request, *, actor_id: str | None, chatbot_id) -> None:
    """Por actor efectivo cuando hay identidad y por IP cuando no.

    Por **actor** y no por credencial: si se contara por PAT, un cliente de confianza que
    atiende a cien personas se llevaría el límite de una sola. Es la misma razón por la que
    la cuota se le carga al actor y no al dueño del token.
    """
    limitar(
        request,
        ambito=f"chat:{chatbot_id}",
        clave=actor_id or ip_de(request),
        regla=_regla("RATE_LIMIT_CHAT", LIMITE_CHAT_POR_DEFECTO),
    )
