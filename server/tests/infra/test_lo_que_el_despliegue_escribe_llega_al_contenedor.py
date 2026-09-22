"""Lo que el despliegue escribe en su fichero de entorno llega de verdad al contenedor.

**El hueco que lo destapó.** El login con Google (#95) salió a producción apagado: `sso-providers`
decía `google: false` y la ruta respondía 404. Los dos **secretos** llegaban —entran por
`env_file` desde `.env.runtime`, que se construye con `secretos.tsv`— y las dos **variables no**,
aunque `deploy.yml` sí las escribía en `.env.despliegue` de la máquina.

La causa: el servicio `app` del compose recibe la configuración no secreta por una **lista
explícita de nombres** en su `environment:`, y añadir la variable a `deploy.yml` no la añade a esa
lista. Son dos ficheros que tienen que decir lo mismo y nada los ataba.

**Por qué los guardarraíles que ya había no lo vieron.** `test_issue42_lo_que_el_codigo_lee_esta_declarado`
cruza lo que el código lee con `.env.example` y con `secretos.tsv`: comprueba que la variable esté
**declarada**. `test_d2_secretos` cruza el inventario de secretos con los guiones que los crean y
los bajan. Ninguno miraba el **cableado del compose**, que es el último tramo — y el tramo donde
una variable declarada, creada y escrita se queda sin llegar.

Es el mismo patrón que este repositorio ya conoce por otros sitios: **tres sitios que tienen que
decir lo mismo y ningún test que los cruce** es la forma en que uno envejece sin que nadie lo
note.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
DEPLOY = RAIZ / ".github" / "workflows" / "deploy.yml"
COMPOSE = RAIZ / "deploy" / "vm" / "docker-compose.vm.yml"

#: El bloque que escribe `.env.despliegue`, y **sólo** ese.
#:
#: Acotarlo importa: `deploy.yml` está lleno de asignaciones de shell —`SHA=`, `ETIQUETA=`,
#: `HAY=`— que no tienen nada que ver con el entorno del contenedor. Un patrón suelto las pesca
#: todas y el guardarraíl se vuelve ruido, que es como se acaba desactivando.
_BLOQUE = re.compile(
    r"tee \$\{DESTINO\}/\.env\.despliegue[^\n]*<<'EOF'\n(.*?)^\s*EOF$",
    re.DOTALL | re.MULTILINE,
)
_ASIGNACION = re.compile(r"^\s*([A-Z][A-Z0-9_]*)=", re.MULTILINE)

#: Variables que el despliegue escribe **para el propio compose**, no para la aplicación: nombran
#: imágenes, o las consume otro servicio. No tienen que estar en el `environment` de `app`.
_NO_SON_PARA_LA_APLICACION = frozenset(
    {
        # Etiquetas de imagen: las lee el compose para saber qué levantar.
        "GOVGENAI_IMAGE",
        "GOVGENAI_FRONTEND_IMAGE",
        "GOVGENAI_SANDBOX_IMAGE",
        "GOVGENAI_MCP_IMAGE",
        # Caddy y el proxy de Cloud SQL, no la aplicación.
        "GOVGENAI_HOST",
        "GOVGENAI_HOST_INSTITUCIONAL",
        "CLOUDSQL_CONNECTION_NAME",
        # El corpus lo sirve Caddy desde el bucket.
        "CORPUS_BUCKET",
    }
)


def _escritas_por_el_despliegue() -> set[str]:
    bloque = _BLOQUE.search(DEPLOY.read_text(encoding="utf-8"))
    assert bloque, (
        "no se encuentra el bloque que escribe `.env.despliegue` en deploy.yml. Si cambió de "
        "forma, este guardarraíl deja de mirar nada y hay que reapuntarlo."
    )
    return set(_ASIGNACION.findall(bloque.group(1)))


def _cableadas_al_contenedor() -> set[str]:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    entorno = compose["services"]["app"].get("environment") or {}
    # El compose admite lista (`- NOMBRE=valor`) y mapa; aquí es mapa, pero se aceptan las dos
    # para que un cambio de estilo no rompa el guardarraíl en vez de avisar de lo suyo.
    if isinstance(entorno, dict):
        return set(entorno)
    return {str(e).split("=", 1)[0].strip() for e in entorno}


def test_el_medidor_lee_los_dos_ficheros() -> None:
    """Un guardarraíl que no encuentra variables pasaría en verde sin comprobar nada."""
    escritas = _escritas_por_el_despliegue()
    cableadas = _cableadas_al_contenedor()
    assert len(escritas) >= 8, f"sólo se ven {len(escritas)} variables en {DEPLOY.name}"
    assert len(cableadas) >= 8, (
        f"sólo se ven {len(cableadas)} en el `environment` de `app`"
    )


def test_lo_que_el_despliegue_escribe_para_la_aplicacion_llega_al_contenedor() -> None:
    faltan = sorted(
        _escritas_por_el_despliegue()
        - _cableadas_al_contenedor()
        - _NO_SON_PARA_LA_APLICACION
    )
    assert not faltan, (
        "El despliegue escribe estas variables en `.env.despliegue` y **no llegan al "
        "contenedor**, porque no están en el `environment:` del servicio `app`:\n  - "
        + "\n  - ".join(faltan)
        + "\n\nAñádelas ahí, o a `_NO_SON_PARA_LA_APLICACION` con su razón si son para el "
        "compose o para otro servicio. Una variable escrita que no llega es un despliegue que "
        "sale en verde con la función apagada — así salió el login con Google la primera vez."
    )


def test_ninguna_exencion_sobra() -> None:
    """Una exención que ya no corresponde a ninguna variable es ruido que confunde al siguiente."""
    escritas = _escritas_por_el_despliegue()
    sobran = sorted(_NO_SON_PARA_LA_APLICACION - escritas)
    assert not sobran, (
        "Estas exenciones no corresponden a ninguna variable que el despliegue escriba: "
        f"{sobran}. Si dejaron de existir, se quitan de la lista."
    )
