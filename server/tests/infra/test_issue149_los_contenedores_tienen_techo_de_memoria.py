"""Issue #149 — ningún contenedor puede llevarse la VM entera por delante.

**Qué pasó.** El 2026-09-24 el sitio estuvo unos 50 minutos sin responder. La VM seguía `RUNNING`
en GCP y no atendía nada: ni HTTP, ni SSH, ni el túnel IAP. La causa fue una consulta sin acotar
ejecutada dentro del contenedor de la aplicación, que se comió la memoria de la máquina.

Lo que lo delató fue la consola serie, que era lo único legible sin SSH: los *health checks* de
los cinco contenedores fallando en bucle, el agente de métricas sin resolver DNS, y el agente de
configuración **sin llegar al servidor de metadatos de la propia VM**. Eso último no es un
problema de red: es una máquina sin recursos para atender nada.

**El defecto no es la consulta, es que una consulta pudiera hacer eso.** Con un techo de memoria
por contenedor, el desenlace habría sido «el contenedor de la aplicación se reinicia» —molesto,
visible y recuperable solo— en vez de «la VM deja de responder y hay que hacerle un `reset` en
seco».

**Los números salen de medir, no de estimar.** Medido en la máquina el 2026-09-24, con el
servicio ya restablecido y atendiendo:

    total 1976 MiB   ·   app 332   sandbox 98   mcp 71   caddy 36   proxy 12   frontend 7

Suman ~557 MiB de contenedores sobre una `e2-small` de 2 GB. Los techos se ponen con holgura
sobre eso —entre dos y tres veces el uso observado, según lo que cada uno pueda crecer— y dejando
libre lo que necesitan el sistema, `dockerd` y los agentes de Google. Que esos agentes tengan aire
no es un detalle de cortesía: **fueron los primeros en caer, y son los que permiten diagnosticar**
cuando ya no se puede entrar.

**Lo que este test NO hace es fijar las cifras.** Comprobar que `app` tiene exactamente 768M
convertiría cualquier ajuste futuro en un rojo que se arregla editando el test, que es la forma
habitual de que un guardarraíl deje de proteger. Lo que fija es lo que no puede volver a pasar:
que un servicio de larga vida corra **sin techo**, y que la suma de los techos supere lo que la
máquina tiene.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "deploy" / "vm" / "docker-compose.vm.yml"

#: Lo que la `e2-small` tiene. Si la máquina cambia, este número cambia con ella — y el test de
#: la suma es el que obliga a mirarlo.
MEMORIA_DE_LA_VM_MIB = 1976

#: Lo que se deja libre para el sistema operativo, `dockerd`, los agentes de Google y la caché de
#: disco. No es un margen de cortesía: los agentes fueron lo primero que murió el 2026-09-24, y
#: son los que dejan diagnosticar una máquina en la que ya no se puede entrar.
RESERVA_DEL_SISTEMA_MIB = 700

#: **No hay exenciones, y `migrate` es la que se planteó.** Corre una vez al desplegar y termina,
#: así que la tentación era dejarla sin techo. Pero «se ejecuta una vez» no es «no puede portarse
#: mal»: una migración sobre una tabla grande es justamente un riesgo de memoria, y además corre
#: **a la vez que el resto**, durante el despliegue, que es el momento en que la máquina va más
#: justa. Una lista de exenciones que empieza con una entrada razonable acaba con cinco.
SIN_TECHO_A_PROPOSITO: set[str] = set()


def _a_mib(valor: str) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*([KMG])i?B?\s*", str(valor), re.IGNORECASE)
    assert m, f"no se entiende el límite de memoria `{valor}`"
    unidad = m.group(2).upper()
    return int(m.group(1)) * {"K": 1 / 1024, "M": 1, "G": 1024}[unidad]


@pytest.fixture(scope="module")
def servicios() -> dict:
    assert COMPOSE.is_file(), f"Falta {COMPOSE.relative_to(RAIZ).as_posix()}"
    datos = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return datos["services"]


def _techo(servicio: dict) -> str | None:
    return (
        (servicio.get("deploy") or {})
        .get("resources", {})
        .get("limits", {})
        .get("memory")
    )


def test_el_medidor_lee_los_servicios(servicios: dict) -> None:
    # Sin esto, un fichero que dejara de parsearse como se espera haría pasar en verde a los dos
    # test de abajo sobre un diccionario vacío.
    assert len(servicios) >= 6, (
        f"se han leído {len(servicios)} servicios del compose de despliegue y se esperaban al "
        f"menos seis. O el fichero cambió de forma, o este test dejó de saber leerlo."
    )
    assert "app" in servicios, "no se encuentra el servicio `app`"


def test_todo_servicio_de_larga_vida_tiene_techo_de_memoria(servicios: dict) -> None:
    sin_techo = [
        nombre
        for nombre, servicio in servicios.items()
        if nombre not in SIN_TECHO_A_PROPOSITO and not _techo(servicio)
    ]
    assert not sin_techo, (
        f"estos servicios corren sin techo de memoria: {sin_techo}. En una `e2-small` de 2 GB, "
        f"uno solo sin límite puede llevarse la máquina entera — y entonces no se cae un "
        f"contenedor, se cae el sitio y encima no se puede entrar a mirar por qué. Pasó el "
        f"2026-09-24 y costó 50 minutos de caída."
    )


def test_los_techos_caben_en_la_maquina(servicios: dict) -> None:
    techos = {
        nombre: _a_mib(t)
        for nombre, servicio in servicios.items()
        if (t := _techo(servicio))
    }
    total = sum(techos.values())
    disponible = MEMORIA_DE_LA_VM_MIB - RESERVA_DEL_SISTEMA_MIB

    assert total <= disponible, (
        f"los techos suman {total} MiB y la máquina deja {disponible} MiB para contenedores "
        f"({MEMORIA_DE_LA_VM_MIB} menos {RESERVA_DEL_SISTEMA_MIB} de reserva). Reparto actual: "
        f"{techos}.\n\n"
        f"Unos techos que no caben no protegen de nada: cada contenedor cree tener permiso para "
        f"crecer hasta el suyo, y si varios lo hacen a la vez el que muere es el sistema. O se "
        f"bajan, o la máquina tiene que crecer — y eso último es una decisión con factura."
    )
