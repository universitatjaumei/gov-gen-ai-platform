"""Issue #43 — ningún `docker compose` del repositorio ancla una imagen por `:latest`.

Con `:latest` no se puede responder a las dos preguntas de cualquier incidente: **qué versión
está corriendo** y **cómo vuelvo a la anterior**. La regla ya estaba adoptada donde más duele
—`deploy.yml` etiqueta sus cuatro imágenes con el SHA del commit, y el compose de la VM ancla
`caddy` y el proxy de Cloud SQL por versión— y estos dos ficheros eran la excepción.

**Y al medirlo apareció algo peor que la falta de reproducibilidad.** `minio/minio` **ya no se
puede tirar de Docker Hub sin credenciales**: el registro responde **401** a un token anónimo y
la API del Hub responde **404** al repositorio, mientras `ollama/ollama` responde **200** por las
dos vías. MinIO publica en `quay.io`, y de allí sale el **mismo build** —mismo `commit-id`—. O
sea que el compose no era sólo poco reproducible: **no arrancaba** para quien lo copiara, ni el
de producción ni el de desarrollo. Que es exactamente lo que va a hacer quien llegue al
repositorio público, y es la razón por la que esta issue estaba en el hito «antes de abrir».

**Y cómo casi me engaño midiéndolo**, que vale más que el dato: `docker run minio/minio:latest`
**funcionó**. No porque el registro la sirviera, sino porque esta máquina tenía una copia de hacía
doce meses en la caché local. Un `docker run` que pasa no dice nada de un registro.

Por eso el arreglo alcanza también a `docker-compose.yml`, el de desarrollo, que la issue no
mencionaba: es el que ejecuta quien clona el repositorio por primera vez.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]

#: Los tres del árbol. Se listan a mano y se comprueba que estén: un `glob` que dejara de
#: encontrarlos pondría este guardarraíl en verde sin mirar nada.
COMPOSES = (
    RAIZ / "docker-compose.yml",
    RAIZ / "docker-compose.prod.yml",
    RAIZ / "deploy" / "vm" / "docker-compose.vm.yml",
)

#: Una imagen anclada bien: `nombre:version`, sin `latest` y con algo que parezca una versión.
_SIN_VERSION = re.compile(r":latest$|^[^:]+$")


def _imagenes(ruta: Path) -> dict[str, str]:
    """`{servicio: imagen}` de un compose, saltándose los que la toman de una variable."""
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    encontradas = {}
    for nombre, cuerpo in (datos.get("services") or {}).items():
        imagen = (cuerpo or {}).get("image")
        # `${GOVGENAI_IMAGE:?…}` es lo contrario del problema: la etiqueta la decide el
        # despliegue, con el SHA del commit, y el compose se niega a arrancar sin ella.
        if imagen and not imagen.startswith("${"):
            encontradas[nombre] = imagen
    return encontradas


def test_los_tres_composes_siguen_donde_se_dice() -> None:
    faltan = [str(c.relative_to(RAIZ)) for c in COMPOSES if not c.is_file()]
    assert not faltan, (
        f"estos compose ya no están donde este guardarraíl los busca: {faltan}. Si se han "
        "movido o retirado, hay que actualizar la lista; si no, el test vigilaría el vacío."
    )


@pytest.mark.parametrize("compose", COMPOSES, ids=lambda c: c.name)
def test_ninguna_imagen_va_sin_version(compose: Path) -> None:
    sueltas = {
        servicio: imagen
        for servicio, imagen in _imagenes(compose).items()
        if _SIN_VERSION.search(imagen)
    }
    assert not sueltas, (
        f"en {compose.name} hay imágenes sin versión fijada: {sueltas}. Con `:latest` no se "
        "puede saber qué está corriendo ni volver atrás, que son las dos preguntas de cualquier "
        "incidente. El despliegue ya etiqueta las suyas con el SHA del commit."
    )


def test_las_imagenes_de_minio_se_toman_de_quay_y_no_de_docker_hub() -> None:
    """Lo que la medición destapó: de Docker Hub ya no se puede tirar sin credenciales.

    Si algún día vuelve a ser pública, este test se pone rojo y habrá que decidir a conciencia
    de dónde se coge, en vez de que el cambio pase inadvertido en un `docker pull` que falla en
    la máquina de otro.
    """
    for compose in COMPOSES:
        for servicio, imagen in _imagenes(compose).items():
            if "minio/" not in imagen:
                continue
            assert imagen.startswith("quay.io/minio/"), (
                f"{compose.name}, servicio «{servicio}»: la imagen es «{imagen}». "
                "`minio/minio` de Docker Hub responde 401 a un token anónimo y 404 en la API "
                "del Hub —medido el 2026-09-19 y contrastado con `ollama/ollama`, que responde "
                "200 por las dos vías—, así que un compose que la pida no arranca para quien no "
                "tenga ya una copia en caché."
            )
