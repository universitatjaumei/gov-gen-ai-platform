"""El ámbito de una tabla de configuración, y la cascada que lo resuelve (MT.1).

Deploy: shared — la regla la usan cloud (que guarda la configuración) y edge (que la aplica).

Nace de una pregunta del usuario: «cambio de organización y sigo viendo los mismos proveedores y
modelos». La auditoría del 2026-08-23 encontró que el núcleo operativo **sí** está acotado, y que
lo que no lo está no lo está por descuido: `hub_llm_configs` nació global sin que nadie lo
decidiera, simplemente porque no había dónde decir lo contrario.

Este módulo pone las dos piezas que faltaban:

1. **Una cascada escrita una vez.** El patrón «nulo = plataforma, se hereda» ya existía dos veces
   —los temas y los valores por defecto de RAG— con dos implementaciones distintas. MT.2…MT.6 lo
   necesitan en cinco tablas más, y cinco copias más habrían garantizado que alguna ordenara mal.
2. **Un guardarraíl.** Toda tabla de `HubConfigBase` declara su ámbito en `__ambito__`; la que no
   lo haga pone rojo el test de MT.1. No documenta: **obliga a decidir**.

**Este módulo no toca comportamiento.** Lo que ya funciona se sustituye en el prompt que lo
cambie, no aquí, para que este no pueda romper nada:

- `hub_themes_router._fusionar` / `_tema_mas_reciente` → los sustituye **MT.2** si la fusión en
  profundidad se generaliza, o se quedan: la de temas funde diccionarios JSON anidados y ésta
  resuelve columnas: son dos problemas, y forzar uno en el otro daría una función con un `if`.
- `config_resolver.get_effective_public_graph_config` (valores por defecto de RAG) → **no** se
  sustituye: superpone columnas de `HubOrganizacion` sobre un `dataclass` de defaults del código,
  que es un nivel más —código → organización → chatbot— y no la cascada de dos de aquí.

**Desviación documentada respecto al plan de MT.1**: el prompt hablaba de *tres* cascadas y
contaba el vocabulario. No lo es: `hub_vocabulary_terms.organizacion_id` es NOT NULL desde
ING.0.1, así que cada organización tiene el suyo y no hay nivel de plataforma que heredar. Queda
declarado como `ORGANIZACION`.

Distinto de `core/auth/tenancy.py`, con el que es fácil confundirlo: aquél decide **quién puede
ver qué** —403 y acotación de listados por el principal—; éste decide **qué fila gana** cuando la
misma configuración está puesta en dos niveles. Uno recibe un usuario y el otro no. Por eso vive
aquí y no dentro de `auth/`, y por eso no se llama `tenancy`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Sequence


class Ambito(StrEnum):
    """De quién es una tabla de configuración.

    Cuatro valores y no tres, porque tres serían una mentira: varias tablas llegan a la
    organización **por otra tabla** (`hub_prompt_templates` por su chatbot) y meterlas en
    «de organización» diría que tienen una columna que no tienen.
    """

    #: Una sola configuración para toda la instalación. No hay nivel de organización.
    PLATAFORMA = "plataforma"
    #: Siempre de una organización: `organizacion_id` NOT NULL. No hay nivel de plataforma.
    ORGANIZACION = "organizacion"
    #: `organizacion_id` nullable. **Nulo = plataforma, y se hereda.**
    HEREDABLE = "heredable"
    #: La organización se alcanza por otra tabla; `via` dice por qué columna.
    DERIVADA = "derivada"


@dataclass(frozen=True)
class AmbitoDeclarado:
    """Lo que una tabla declara sobre sí misma.

    `via` sólo tiene sentido en `DERIVADA`, y ahí es obligatorio: «derivada» a secas no le
    sirve a nadie que lea el inventario de MT.7, que es donde esto acaba.
    """

    ambito: Ambito
    via: str | None = None


class AmbitoNoDeclarado(RuntimeError):
    """Una tabla de configuración que no dice de quién es, o lo dice a medias."""


def declarar(ambito: Ambito, *, via: str | None = None) -> AmbitoDeclarado:
    """Azúcar para el `__ambito__` de un modelo, y el sitio donde se valida la combinación."""
    if ambito is Ambito.DERIVADA and not via:
        raise AmbitoNoDeclarado(
            "Un ámbito derivado tiene que decir por qué columna se llega a la organización"
        )
    return AmbitoDeclarado(ambito=ambito, via=via)


def ambito_de(modelo: Any) -> AmbitoDeclarado:
    """El ámbito declarado por un modelo, o `AmbitoNoDeclarado` si no lo declara.

    Se mira **la clase, no su ascendencia**: con `getattr` un modelo que heredara de otro se
    quedaría con el ámbito del padre sin decir nada, que es exactamente el olvido silencioso que
    este módulo existe para impedir. Heredar de una base común es normal; heredar la decisión de
    quién es el dueño de los datos, no.
    """
    declarado = (
        modelo.__dict__.get("__ambito__")
        if isinstance(modelo, type)
        else getattr(modelo, "__ambito__", None)
    )
    if declarado is None:
        raise AmbitoNoDeclarado(
            f"{getattr(modelo, '__tablename__', modelo)} no declara `__ambito__`"
        )
    if isinstance(declarado, Ambito):
        # Se admite la forma corta `__ambito__ = Ambito.PLATAFORMA`, que es la de casi todas.
        # `DERIVADA` no cabe en ella, y esto es lo que lo impide.
        return declarar(declarado)
    return declarado


def tablas_sin_ambito() -> list[str]:
    """Las tablas de `HubConfigBase` que no declaran ámbito. Vacío = todas lo declaran.

    Se recorre el registro de SQLAlchemy y no una lista escrita a mano: una lista a mano no se
    actualiza al añadir una tabla, que es exactamente el caso que este guardarraíl existe para
    cazar.
    """
    from server.app.modules.agents_hub.database.config_models import HubConfigBase

    sin_declarar: list[str] = []
    for mapper in HubConfigBase.registry.mappers:
        modelo = mapper.class_
        try:
            ambito_de(modelo)
        except AmbitoNoDeclarado:
            sin_declarar.append(modelo.__tablename__)
    return sorted(sin_declarar)


# ─────────────────────────── La cascada ───────────────────────────


def de_esta_organizacion(filas: Iterable[Any], organizacion_id: uuid.UUID | None) -> Any | None:
    """La fila de esta organización, o `None`. **Nunca la de otra.**

    Comparado como texto porque en el camino de un endpoint el identificador llega a veces como
    `str` y a veces como `UUID`, y `UUID("…") != "…"`: una comparación estricta haría que la
    cascada no encontrara la fila propia y cayera a plataforma en silencio.
    """
    if organizacion_id is None:
        return None
    buscado = str(organizacion_id)
    for fila in filas:
        propietaria = getattr(fila, "organizacion_id", None)
        if propietaria is not None and str(propietaria) == buscado:
            return fila
    return None


def de_plataforma(filas: Iterable[Any]) -> Any | None:
    """La fila del nivel plataforma: la que no es de ninguna organización."""
    for fila in filas:
        if getattr(fila, "organizacion_id", None) is None:
            return fila
    return None


def resolver_cascada(
    filas: Sequence[Any],
    organizacion_id: uuid.UUID | None,
    *,
    campos: Sequence[str],
) -> dict[str, Any]:
    """Los campos resueltos para una organización: plataforma debajo, la suya encima.

    **Campo a campo, no fila entera.** Con reemplazo de fila, una organización que sólo quiere
    cambiar un color tendría que repetir la configuración completa para no perder el resto — y en
    cuanto la plataforma cambiara algo, lo suyo se quedaría congelado sin que nadie lo notara. Es
    la misma razón por la que la cascada de temas funde en profundidad.

    `None` en la fila de la organización significa **heredar**; `""` o `0` significan «lo quiero
    así». Colapsar los dos haría imposible vaciar un valor heredado desde la pantalla.

    Sólo participan dos filas: la de plataforma y la de esta organización. Las de las demás no se
    miran, y eso no es una optimización — es la diferencia entre resolver y filtrar la
    configuración del municipio de al lado.
    """
    base = de_plataforma(filas)
    propia = de_esta_organizacion(filas, organizacion_id)

    resuelto: dict[str, Any] = {}
    for campo in campos:
        valor = getattr(propia, campo, None) if propia is not None else None
        if valor is None:
            valor = getattr(base, campo, None) if base is not None else None
        resuelto[campo] = valor
    return resuelto
