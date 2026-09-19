"""Issue #46 — no queda ningún `TODO` vivo en `server/app/`.

`AGENTS.md` lo dice sin matices: los comentarios `TODO`, `deprecated` o `legacy` son **deuda
técnica disfrazada**, y el historial de git es la fuente de verdad del pasado. Un `TODO` en el
código no lo lee nadie que pueda decidir sobre él; una issue sí.

El que había no era cosmético. En `anonymizer.py` decía que el determinismo se obtiene por
instancia «no por persistencia cifrada (TODO post-MVP)», y eso **contradecía una decisión ya
tomada y escrita en otros dos sitios del mismo módulo**: `run_context.py` tiene como regla dura
que «los mapas forward/reverse NUNCA se persisten en BD», y `service.py` guarda por qué —decisión
del 2026-08-24: el piloto no trata datos de ciudadanos, así que no hay bóveda cifrada antes del
piloto— y hasta el nombre del trabajo futuro, **F2.A.4 (Vault Edge)**, que se escribirá cuando
haya quien lo consuma. O sea que el `TODO` anunciaba como pendiente algo que ya estaba decidido y
presupuestado. Eso es peor que no decir nada: quien lo leyera creería que falta por decidir.

**Qué cuenta como `TODO` vivo, y qué no.** Contar apariciones de la palabra no sirve: en
`hub_ingestion_router.py` hay una frase que explica que allí **vivió** un
``# TODO: Validar que el usuario tiene acceso al chatbot`` y lo que costó tenerlo abierto. Eso es
justo lo que este proyecto quiere que se escriba —el pasado, con su precio— y va entre comillas
invertidas. Un guardarraíl que lo marcara empujaría a borrar la explicación para poner el test en
verde, que es la peor forma de gastar un test.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APP = RAIZ / "server" / "app"

#: Lo que se persigue: la palabra como marca de trabajo pendiente. Las apariciones dentro de
#: comillas invertidas se quitan antes, porque ésas son citas de lo que hubo.
_MARCA = re.compile(r"\bTODO\b|\bFIXME\b|\bXXX\b")
_CITADO = re.compile(r"`[^`]*`")


def _lineas_con_marca(fichero: Path) -> list[str]:
    encontradas = []
    for numero, linea in enumerate(
        fichero.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        if _MARCA.search(_CITADO.sub("", linea)):
            encontradas.append(f"{fichero.relative_to(RAIZ)}:{numero}: {linea.strip()}")
    return encontradas


def test_no_hay_marcas_de_trabajo_pendiente_en_la_aplicacion() -> None:
    culpables: list[str] = []
    for fichero in APP.rglob("*.py"):
        if "__pycache__" in fichero.parts:
            continue
        culpables.extend(_lineas_con_marca(fichero))

    assert not culpables, (
        "Quedan marcas de trabajo pendiente en `server/app/`:\n  - "
        + "\n  - ".join(culpables)
        + "\n\nUn `TODO` en el código no lo lee nadie que pueda decidir sobre él. O se hace, o "
        "se decide y se escribe la decisión, o se abre una issue y el código remite a ella."
    )


def test_la_cita_historica_del_router_no_cuenta() -> None:
    """El caso negativo, comprobado: si lo marcara, el test empujaría a borrar la explicación.

    `hub_ingestion_router.py` cuenta que allí vivió un `TODO` de autorización y lo que costó
    tenerlo abierto. Es exactamente lo que este proyecto quiere escrito.
    """
    router = APP / "routers" / "hub_ingestion_router.py"
    texto = router.read_text(encoding="utf-8")
    assert "TODO" in texto, (
        "la explicación histórica del `TODO` de autorización ha desaparecido de "
        "`hub_ingestion_router.py`. No hacía falta borrarla: iba entre comillas invertidas."
    )
    assert not _lineas_con_marca(router), (
        "la cita histórica ha dejado de ir entre comillas invertidas, así que ahora el "
        "guardarraíl la marca como trabajo pendiente."
    )


def test_la_decision_sobre_la_persistencia_esta_escrita_donde_se_lee() -> None:
    """Cerrar un `TODO` es escribir la decisión, no borrar la palabra."""
    anonimizador = (
        APP / "modules" / "redaccion" / "services" / "anonymization" / "anonymizer.py"
    ).read_text(encoding="utf-8")
    assert "F2.A.4" in anonimizador, (
        "el docstring del anonimizador ya no dice dónde vive la persistencia del mapa. Sin esa "
        "referencia, quien lea «no por persistencia cifrada» no sabe si es una decisión o un "
        "olvido, que es justo lo que pasaba con el `TODO`."
    )
