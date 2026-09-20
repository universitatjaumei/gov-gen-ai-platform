"""`server` declara las versiones de Python que de verdad soporta, y no más.

**Lo que lo destapó.** El 2026-09-20 el trabajo de Dependabot sobre `/server` **fallaba**, y
llevaba haciéndolo sin que nadie lo viera porque su rojo no aparece en ningún check de PR: es un
trabajo propio de Dependabot. Tres errores, todos la misma forma —`fsspec`, `gcsfs` y `s3fs`—:

    No solution found when resolving dependencies for split
    (markers: python_full_version >= '3.14' and sys_platform != 'darwin')

`datasets`, que entra por el extra `evaluacion`, acota `fsspec` por debajo de lo que piden
`gcsfs` y `s3fs` en sus versiones nuevas. Para **3.13 hay solución** y por eso el lock existe y
CI pasa; para **3.14 no la hay**. Y Dependabot resuelve para **todas** las versiones que el
manifiesto dice soportar, no sólo para la que se ejecuta.

**La causa no era la restricción, era la declaración.** `requires-python` decía `>=3.11` mientras
la imagen y CI corren **3.13 y sólo 3.13**. O sea que el manifiesto prometía soporte para cuatro
versiones que nadie ejecuta, prueba ni despliega, y una de esas promesas es la que bloqueaba las
actualizaciones. Declarar lo que se soporta de verdad no es una restricción nueva: es dejar de
afirmar de más.

**Se midió antes de aplicarlo**: al reducir el rango, el lock pierde **un solo paquete**
—`tomli`, el respaldo de `tomllib` para Pythons anteriores a la 3.11— y el conjunto que se
despliega queda **idéntico**, 200 paquetes.

**Por qué lleva tope superior**, que en una biblioteca sería mala práctica: esto no es una
biblioteca, es una aplicación que se despliega en una imagen con la versión fijada. Decir
`<3.14` es describir el despliegue, no limitar a nadie. Y si algún día se sube, se sube aquí y en
el `Dockerfile` a la vez, que es justo lo que este fichero obliga a hacer.

**Los otros tres proyectos se midieron y están bien**: sus trabajos de Dependabot pasan
(`mcp_server`, `shared`, `services/script_sandbox`), así que no se tocan. Cambiar lo que funciona
por simetría es cómo se rompen las cosas que nadie estaba mirando.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MANIFIESTO = RAIZ / "server" / "pyproject.toml"
DOCKERFILE = RAIZ / "Dockerfile"


def _python_de_la_imagen() -> str:
    """La versión que instala la imagen que se despliega, leída del `Dockerfile`."""
    versiones = re.findall(r"^FROM python:(\d+\.\d+)", DOCKERFILE.read_text(encoding="utf-8"), re.M)
    assert versiones, "el `Dockerfile` ya no parte de una imagen `python:X.Y`"
    assert len(set(versiones)) == 1, (
        f"las etapas del `Dockerfile` usan Pythons distintos: {sorted(set(versiones))}. "
        "Construir con uno y ejecutar con otro es una diferencia que aparece en producción."
    )
    return versiones[0]


def _rango_declarado() -> str:
    datos = tomllib.loads(MANIFIESTO.read_text(encoding="utf-8"))
    return datos["project"]["requires-python"]


def test_el_minimo_declarado_es_el_de_la_imagen() -> None:
    imagen = _python_de_la_imagen()
    rango = _rango_declarado()
    assert f">={imagen}" in rango, (
        f"el manifiesto declara «{rango}» y la imagen ejecuta Python {imagen}. Declarar de más "
        "no es generosidad: Dependabot resuelve para **todas** las versiones prometidas, y una "
        "sola sin solución le impide proponer actualizaciones en todo el proyecto. Pasó el "
        "2026-09-20 con `fsspec`, `gcsfs` y `s3fs` en la 3.14."
    )


def test_hay_tope_superior_y_deja_fuera_la_siguiente() -> None:
    """El tope es lo que evita que Dependabot resuelva para versiones que nadie ejecuta."""
    imagen = _python_de_la_imagen()
    mayor, menor = imagen.split(".")
    siguiente = f"{mayor}.{int(menor) + 1}"
    rango = _rango_declarado()
    assert f"<{siguiente}" in rango, (
        f"«{rango}» no acota por arriba en {siguiente}. En una biblioteca sería mala práctica; "
        "esto es una aplicación que se despliega en una imagen con la versión fijada, así que el "
        "tope **describe** el despliegue. Sin él vuelve el fallo de resolución de Dependabot."
    )


def test_ci_prueba_con_esa_misma_version() -> None:
    """Y que no se pruebe con una y se despliegue con otra, que es el otro modo de fallo."""
    ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    matriz = re.search(r"python-version:\s*\[([^\]]+)\]", ci)
    assert matriz, "no encuentro la matriz de versiones de Python en `ci.yml`"
    versiones = {v.strip().strip('"\'') for v in matriz.group(1).split(",")}
    assert versiones == {_python_de_la_imagen()}, (
        f"CI prueba con {sorted(versiones)} y la imagen ejecuta {_python_de_la_imagen()}. "
        "Probar con una versión y desplegar con otra deja el hueco en el sitio donde no hay "
        "tests."
    )
