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
habitual de que un guardarraíl deje de proteger. Lo que fija es lo que no puede volver a pasar.

**Y lo que no puede volver a pasar cambió el 2026-09-25**, cuando la memoria pasó a
sobreasignarse: los techos ya no se reparten como cuotas, porque `limits.memory` no aparta nada
—Docker sólo mata a quien lo supera— y repartirlos dejaba media máquina ociosa que nadie podía
tocar ni en su pico. Con 1.264 MiB repartidos de 1.976, la reingesta del corpus murió por OOM
contra su techo mientras sobraban 700 MiB sin dueño.

Las cuatro cosas que se comprueban ahora:

1. que ningún servicio de larga vida corra **sin techo**;
2. que todo el que tenga techo **declare su reserva** —si no, el punto 3 pasaría sobre una lista
   vacía, que es el modo silencioso en que un guardarraíl deja de mirar—;
3. que la suma de las **reservas** quepa, porque ésa sí es la promesa de uso sostenido;
4. y que **ningún techo suelto** supere la máquina entera, que es lo que convierte la
   sobreasignación en barra libre.

La suma de los techos, en cambio, **excede la RAM a propósito**: el razonamiento de por qué los
picos no coinciden está escrito en la cabecera del propio compose, que es donde se cambia.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "deploy" / "vm" / "docker-compose.vm.yml"

#: Lo que la máquina tiene. Si cambia, este número cambia con ella — y los dos test de abajo son
#: los que obligan a mirarlo.
#:
#: **`e2-medium` desde el 2026-09-25.** Estuvo en `e2-small` (1.976 MiB) hasta que la reingesta
#: del corpus no cupo: el cargador confirma una transacción por asistente, así que retiene todo lo
#: que va a escribir, y la Ley 9/2017 —4.330 fragmentos— murió con exit 137 contra un techo de
#: 768M. Un documento es la unidad mínima de carga, o sea que no había forma de trocearlo más.
MEMORIA_DE_LA_VM_MIB = 3924

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


def _reserva(servicio: dict) -> str | None:
    """Lo que el contenedor declara que espera usar; `reservations.memory` del compose.

    Compose la aplica también fuera de Swarm, comprobado en la VM: un servicio con
    `limits: 300M` / `reservations: 100M` llega al contenedor como `Memory=314572800` y
    `MemoryReservation=104857600`.
    """
    return (
        (servicio.get("deploy") or {})
        .get("resources", {})
        .get("reservations", {})
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


def test_todo_servicio_con_techo_declara_su_reserva(servicios: dict) -> None:
    """Sin esto, el test de la suma de reservas pasa en verde sobre una lista vacía.

    Es el fallo que ya se ha pagado dos veces en este repositorio: un guardarraíl que recorre algo
    que no existe no falla, **da verde**, y un verde no llama la atención de nadie. Aquí bastaría
    con que alguien quitara los bloques `reservations` para que «las reservas caben» fuera cierto
    y completamente vacío de contenido.

    Y hay un motivo de fondo: sin reserva declarada, un contenedor sólo tiene techo, y el techo
    está sobreasignado a propósito. Es decir, no habría ningún número que diga lo que ese servicio
    espera usar de verdad, que es lo único con lo que se puede comprobar que la máquina no está
    sobrevendida en el caso normal.
    """
    sin_reserva = [
        nombre
        for nombre, servicio in servicios.items()
        if _techo(servicio) and not _reserva(servicio)
    ]

    assert not sin_reserva, (
        f"estos servicios tienen techo pero no declaran reserva: {sin_reserva}. El techo está "
        f"sobreasignado a propósito —los picos no coinciden—, así que la reserva es el único "
        f"número que dice cuánto espera usar cada uno en marcha normal. Sin ella no se puede "
        f"comprobar que la máquina aguanta, y el test que lo comprueba pasaría sobre una lista "
        f"vacía sin enterarse."
    )


def test_las_reservas_caben_en_la_maquina(servicios: dict) -> None:
    """Lo que tiene que caber son las RESERVAS, no los techos.

    **Este test comprobaba la suma de los techos y se cambió el 2026-09-25.** No porque estorbara
    —un guardarraíl que estorba se arregla, no se afloja— sino porque medía lo que no era.
    `limits.memory` es un techo por contenedor y Docker **no aparta** esa memoria: sólo mata a
    quien lo supere. Exigir que los techos sumen menos que la RAM reparte la máquina en cuotas y
    deja ociosa la mitad, que es lo que pasaba: 1.264 MiB repartidos de 1.976, y la reingesta del
    corpus muriendo por OOM contra un techo de 768 mientras sobraban 700 que nadie podía tocar.

    Lo que sí es una promesa de uso es `reservations.memory`, y Compose lo aplica también fuera de
    Swarm. Si las reservas no caben, la máquina está sobrevendida de verdad.
    """
    reservas = {
        nombre: _a_mib(r)
        for nombre, servicio in servicios.items()
        if (r := _reserva(servicio))
    }
    total = sum(reservas.values())
    disponible = MEMORIA_DE_LA_VM_MIB - RESERVA_DEL_SISTEMA_MIB

    assert total <= disponible, (
        f"las reservas suman {total} MiB y la máquina deja {disponible} MiB para contenedores "
        f"({MEMORIA_DE_LA_VM_MIB} menos {RESERVA_DEL_SISTEMA_MIB} de reserva). Reparto actual: "
        f"{reservas}.\n\n"
        f"Una reserva es lo que el contenedor espera usar de forma sostenida. Si la suma no cabe, "
        f"la máquina está sobrevendida en el caso NORMAL, no en el pico — y eso no se arregla "
        f"escalonando picos: o se bajan, o la máquina tiene que crecer."
    )


def test_ningun_techo_suelto_supera_la_maquina(servicios: dict) -> None:
    """Sobreasignar es repartir picos que no coinciden; no es dar barra libre a uno solo.

    La sobreasignación se sostiene sobre que los picos no son concurrentes. Ese argumento deja de
    valer en cuanto **un** contenedor puede, él solo, agotar la máquina: entonces el que mata ya no
    es el cgroup sino el OOM del kernel, que elige a su criterio y se lleva por delante a los
    agentes de Google — que fueron los primeros en caer el 2026-09-24 y son justo los que permiten
    diagnosticar cuando ya no se puede entrar.
    """
    disponible = MEMORIA_DE_LA_VM_MIB - RESERVA_DEL_SISTEMA_MIB
    pasados = {
        nombre: _a_mib(t)
        for nombre, servicio in servicios.items()
        if (t := _techo(servicio)) and _a_mib(t) > disponible
    }

    assert not pasados, (
        f"estos techos superan por sí solos lo que la máquina deja para contenedores "
        f"({disponible} MiB): {pasados}.\n\n"
        f"Un techo así no acota nada: el contenedor llega al límite de la máquina antes que al "
        f"suyo, y entonces no muere él, muere el sistema."
    )
