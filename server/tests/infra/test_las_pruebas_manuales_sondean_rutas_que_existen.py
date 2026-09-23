"""Un guion de pruebas manuales no sondea rutas que el despliegue no sirve.

**El fallo que lo trae.** `pruebas_manuales_despliegue.bat` comprobaba `/api/v1/health` —que no
existe: la aplicación registra `/health`— y `/hub` —que tampoco: el panel está en `/panel/`—, y
las dos líneas de al lado decían «QUE DEBES VER: 200». Las escribí de memoria el mismo día que
abrí la issue #104, que va justo de que `/hub` devuelve el XML del *bucket*.

Un guion manual que miente en su primer paso es peor que no tenerlo: quien lo siga verá un 404,
supondrá que el despliegue está roto, y perderá el rato en un fallo que no existe. O peor, se
acostumbrará a que ese paso «siempre sale mal» y dejará de mirarlo.

**Se comprueba contra el `Caddyfile`, que es quien reparte.** Lo que decide si una dirección
llega a un servicio o al *bucket* del corpus es el proxy, y el `handle` final —el que cae al
*bucket*— es el que hace que una ruta equivocada parezca existir.

**Lo que este guardarraíl NO cubre, dicho para que nadie lo dé por cubierto.** Una ruta bajo
`/api/` pasa el reparto de Caddy y puede morir igualmente con un 404 en FastAPI: es el caso de
`/api/v1/health`. Se intentó cruzarlo contra `app.routes` y **la medida no era fiable** —el
registro de routers es condicional y ahí sólo se veían 45 de las 181 rutas del contrato—, así
que se quitó en vez de dejar un guardarraíl que mide mal. Media comprobación honesta vale más
que una entera que miente.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
CADDYFILE = RAIZ / "deploy" / "vm" / "Caddyfile"
GUION = RAIZ / "pruebas_manuales" / "pruebas_manuales_despliegue.bat"

#: Las rutas que el guion sondea con `curl`, tal como las escribe: `%SITIO%/loquesea`.
_SONDEADA = re.compile(r"%SITIO%(/\S*)")


def _rutas_del_guion() -> list[str]:
    texto = GUION.read_text(encoding="cp1252")
    return sorted({m.group(1).rstrip('"') for m in _SONDEADA.finditer(texto)})


def _prefijos_que_sirve_la_aplicacion() -> set[str]:
    """Lo que el `Caddyfile` manda a un servicio, y no al *bucket* del corpus.

    Se leen los `handle` con ruta y los *matchers* con nombre (`@panel path /panel /panel/*`).
    El `handle` sin argumento es el que cae al *bucket*, y por eso no cuenta: es justo el que
    hace que una ruta equivocada parezca existir.
    """
    texto = CADDYFILE.read_text(encoding="utf-8")
    prefijos: set[str] = set()
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("@") and " path " in limpia:
            prefijos.update(re.findall(r"(/\S+)", limpia.split(" path ", 1)[1]))
        elif limpia.startswith("handle /"):
            prefijos.update(re.findall(r"(/\S+)", limpia[len("handle "):].split("{")[0]))
    return prefijos


def _la_sirve(ruta: str, prefijos: set[str]) -> bool:
    for prefijo in prefijos:
        if prefijo.endswith("/*"):
            if ruta.startswith(prefijo[:-1]):
                return True
        elif ruta == prefijo or ruta.rstrip("/") == prefijo.rstrip("/"):
            return True
    # La raíz la sirve el `handle` final, que es el sitio del corpus: eso sí existe.
    return ruta == "/"


def test_el_medidor_lee_los_dos_ficheros() -> None:
    """Un guardarraíl que no encuentra nada pasa en verde sin comprobar nada."""
    assert len(_rutas_del_guion()) >= 4, f"sólo veo {_rutas_del_guion()} en {GUION.name}"
    assert len(_prefijos_que_sirve_la_aplicacion()) >= 3


def test_ninguna_ruta_sondeada_cae_en_el_bucket() -> None:
    prefijos = _prefijos_que_sirve_la_aplicacion()
    huerfanas = [r for r in _rutas_del_guion() if not _la_sirve(r, prefijos)]
    assert huerfanas == [], (
        "el guion de pruebas manuales sondea rutas que el `Caddyfile` **no** manda a ningún "
        f"servicio, así que caen en el *bucket* del corpus y devuelven 404: {huerfanas}\n\n"
        f"Lo que sí sirve: {sorted(prefijos)}. Si la ruta es nueva, añádela al `Caddyfile`; si "
        "está mal escrita, corrígela en el guion."
    )
