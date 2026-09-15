"""La lista de avisos aceptados no crece sola: cada entrada caduca, y el rojo lo pone esto.

Un fichero de avisos aceptados sin nada que lo vigile es una lista de exclusiones con mejor
prosa. Lo que separa una cosa de la otra es que **aceptar cueste algo**: si renovar fuera gratis
y silencioso, la lista crecería hasta cubrir el árbol entero y la puerta de `supply-chain`
quedaría encendida y sin efecto — que es exactamente la avería que DEP.7 existe para evitar.

Este fichero comprueba cuatro cosas, y las cuatro salieron de pensar cómo se degrada la lista:

* **Cada entrada tiene los cinco campos.** Una aceptación sin `motivo` no se puede rebatir, y una
  sin `acepta` no tiene a quién preguntar.
* **Ninguna aceptación ha caducado.** Es la pieza que hace que la lista se revise: el rojo llega
  solo, con fecha, y obliga a mirar de nuevo.
* **El motivo dice algo.** Un `motivo = "no aplica"` es una casilla rellenada, no una razón.
* **La caducidad no es eterna.** Aceptar algo durante tres años es no aceptarlo: es olvidarlo con
  permiso.

Y el caso negativo se comprueba de verdad (`test_una_aceptacion_caducada_pone_rojo`): un
guardarraíl que nunca se ha visto fallar no es un guardarraíl, es una afirmación. Este proyecto ya
se comió un test que recorría un directorio inexistente y pasaba en verde.
"""

from __future__ import annotations

import datetime as dt
import tomllib
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[3]
FICHERO = RAIZ / "avisos_aceptados.toml"

CAMPOS = ("id", "paquete", "motivo", "acepta", "caduca")

#: Más allá de esto, «aceptado» quiere decir «olvidado». Seis meses da margen para esperar a que
#: un padre levante un techo, y no tanto como para que nadie vuelva a mirarlo.
MAXIMO_DE_DIAS = 190


def _carga(texto: str) -> list[dict[str, Any]]:
    return tomllib.loads(texto).get("aviso", [])


@pytest.fixture(scope="module")
def avisos() -> list[dict[str, Any]]:
    assert FICHERO.is_file(), (
        f"Falta {FICHERO.relative_to(RAIZ).as_posix()}. La puerta de `supply-chain` lo lee para "
        f"saber qué avisos están aceptados a propósito; sin el fichero, o bloquea por cosas que "
        f"ya se decidieron, o alguien lo desactiva."
    )
    return _carga(FICHERO.read_text(encoding="utf-8"))


def test_cada_aceptacion_lleva_los_cinco_campos(avisos: list[dict[str, Any]]) -> None:
    for i, aviso in enumerate(avisos):
        faltan = [c for c in CAMPOS if not str(aviso.get(c, "")).strip()]
        assert not faltan, (
            f"La aceptación #{i + 1} ({aviso.get('id', '¿sin id?')}) no tiene {faltan}. Los cinco "
            f"campos son lo único que separa esta lista de una lista de exclusiones: sin "
            f"`motivo` no se puede rebatir, sin `acepta` no hay a quién preguntar, y sin "
            f"`caduca` nadie vuelve a mirarlo."
        )


def test_ninguna_aceptacion_ha_caducado(avisos: list[dict[str, Any]]) -> None:
    hoy = dt.date.today()
    caducadas = []
    for aviso in avisos:
        caduca = aviso["caduca"]
        if isinstance(caduca, str):
            caduca = dt.date.fromisoformat(caduca)
        if isinstance(caduca, dt.datetime):
            caduca = caduca.date()
        if caduca < hoy:
            caducadas.append(f"{aviso['id']} ({aviso['paquete']}, caducó el {caduca})")

    assert not caducadas, (
        "Estas aceptaciones han caducado y hay que volver a mirarlas:\n  - "
        + "\n  - ".join(caducadas)
        + "\n\nVolver a mirar quiere decir comprobar si la corrección ya se puede aplicar. Si se "
        "puede, se sube el paquete y la entrada SE BORRA. Si sigue sin poderse, se actualiza el "
        "motivo con lo que se ha comprobado y se pone fecha nueva. Cambiar sólo la fecha es "
        "convertir esto en una lista de exclusiones."
    )


def test_el_motivo_dice_algo(avisos: list[dict[str, Any]]) -> None:
    vacuos = {"no aplica", "no nos afecta", "falso positivo", "n/a", "-", "pendiente"}
    for aviso in avisos:
        motivo = " ".join(aviso["motivo"].split())
        assert len(motivo) >= 40, (
            f"El motivo de {aviso['id']} son {len(motivo)} caracteres. Una aceptación tiene que "
            f"poder rebatirse dentro de un año por alguien que no estaba: hay que decir por qué "
            f"no se puede arreglar hoy y qué habría que comprobar al renovar."
        )
        assert motivo.strip().lower().rstrip(".") not in vacuos, (
            f"El motivo de {aviso['id']} es una casilla rellenada, no una razón."
        )


def test_la_caducidad_no_es_eterna(avisos: list[dict[str, Any]]) -> None:
    hoy = dt.date.today()
    for aviso in avisos:
        caduca = aviso["caduca"]
        if isinstance(caduca, str):
            caduca = dt.date.fromisoformat(caduca)
        if isinstance(caduca, dt.datetime):
            caduca = caduca.date()
        dias = (caduca - hoy).days
        assert dias <= MAXIMO_DE_DIAS, (
            f"{aviso['id']} está aceptado {dias} días, y el máximo son {MAXIMO_DE_DIAS}. Una "
            f"caducidad lo bastante lejana es no tener caducidad: nadie vuelve a mirar algo que "
            f"vence después de que el proyecto haya cambiado de manos."
        )


def test_una_aceptacion_caducada_pone_rojo() -> None:
    """El caso negativo. Un guardarraíl que nunca se ha visto fallar es una afirmación."""
    ayer = dt.date.today() - dt.timedelta(days=1)
    caducado = _carga(
        f'[[aviso]]\n'
        f'id = "PYSEC-0000-0000"\n'
        f'paquete = "ejemplo"\n'
        f'motivo = "Entrada de prueba para comprobar que el guardarrail se pone rojo de verdad."\n'
        f'acepta = "Nadie"\n'
        f'caduca = "{ayer.isoformat()}"\n'
    )
    with pytest.raises(AssertionError, match="han caducado"):
        test_ninguna_aceptacion_ha_caducado(caducado)


def test_un_motivo_vacuo_pone_rojo() -> None:
    """El otro caso negativo: rellenar la casilla no es aceptar."""
    vacuo = _carga(
        '[[aviso]]\n'
        'id = "PYSEC-0000-0001"\n'
        'paquete = "ejemplo"\n'
        'motivo = "no aplica"\n'
        'acepta = "Nadie"\n'
        'caduca = "2099-01-01"\n'
    )
    with pytest.raises(AssertionError):
        test_el_motivo_dice_algo(vacuo)
