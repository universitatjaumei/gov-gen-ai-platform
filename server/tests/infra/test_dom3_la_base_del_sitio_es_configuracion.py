"""La base del sitio publicado es configuración, y sólo hay una (DOM.3).

Cada respuesta del asistente enlaza `…/html/<norma>.html#art-63`, y eso es lo que la gente
guarda y comparte. Ese enlace lo construye `citations.py` con `CORPUS_SITE_BASE_URL`, y en
DOM.3 esa variable pasa del bucket al dominio institucional. La forma de la URL **no cambia**:
cambiar la base rompe los enlaces ya enviados una vez; cambiar la forma los rompería otra.

Dos cosas se fijan aquí, y las dos son de las que no dan error cuando se rompen:

* **Ni el dominio ni el bucket aparecen escritos en el servidor.** Hoy la configuración vive
  en las variables del repositorio de GitHub, que es de donde `deploy.yml` escribe
  `.env.despliegue`; un literal en el código convertiría un cambio de despliegue en un cambio
  de código, y —peor— dejaría dos verdades donde la comprobación de la cita mira una.
* **El despliegue pasa las tres variables.** Una que falte no rompe el arranque: deja las
  citas apuntando a donde apuntaban, o el preflight rechazando al origen nuevo, y eso se
  descubre cuando alguien abre un enlace.

Lo que este fichero **no** puede comprobar, y por eso se verifica a mano en DOM.5: que las
variables del repositorio tengan el valor bueno. Viven en GitHub, no en el árbol.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APP = RAIZ / "server" / "app"
CITAS = APP / "modules" / "agents_hub" / "services" / "retrieval" / "citations.py"
DESPLIEGUE = RAIZ / ".github" / "workflows" / "deploy.yml"

# Nombres concretos del despliegue de la UJI. Son los que no deben aparecer en el código.
NOMBRES_DEL_DESPLIEGUE = ("normativa.uji.es", "storage.googleapis.com", "sslip.io")


def _texto(ruta: Path) -> str:
    assert ruta.is_file(), f"Falta {ruta.relative_to(RAIZ).as_posix()}"
    return ruta.read_text(encoding="utf-8")


def test_la_cita_lee_la_base_del_entorno() -> None:
    texto = _texto(CITAS)
    assert re.search(r"os\.getenv\(\s*BASE_DEL_SITIO", texto), (
        "La base del sitio se lee del entorno en el momento de citar. Leerla al importar "
        "dejaría el valor congelado del arranque, y entonces cambiar la variable exigiría "
        "reconstruir la imagen en vez de reiniciar."
    )
    assert 'BASE_DEL_SITIO = "CORPUS_SITE_BASE_URL"' in texto, (
        "El nombre de la variable se declara una vez y los tests lo importan de ahí."
    )


def test_la_forma_de_la_url_de_una_norma_no_cambia() -> None:
    """`{base}/html/{slug}.html{#ancla}`. Es la promesa del guion de publicación.

    «La URL de una norma no puede cambiar entre publicaciones»: lo dice
    `scripts/publica_sitio_corpus.sh` como regla dura, porque es la que cita el asistente y la
    que la gente guarda. DOM.3 cambia la base y **sólo** la base.
    """
    texto = _texto(CITAS)
    assert re.search(r'f"\{base\}/html/\{slug\}\.html\{_fragmento\(metadata\)\}"', texto), (
        "La forma de la URL cambió. Si es a propósito, hay que republicar las 313 páginas y "
        "aceptar que los enlaces ya enviados en correos y actas dejan de resolver."
    )


def test_ningun_nombre_del_despliegue_esta_escrito_en_el_servidor() -> None:
    encontrados: list[str] = []
    for fichero in APP.rglob("*.py"):
        texto = fichero.read_text(encoding="utf-8")
        for numero, linea in enumerate(texto.splitlines(), 1):
            for nombre in NOMBRES_DEL_DESPLIEGUE:
                if nombre in linea:
                    encontrados.append(
                        f"{fichero.relative_to(RAIZ).as_posix()}:{numero}: {linea.strip()}"
                    )
    assert not encontrados, (
        "Nombres del despliegue escritos en el servidor. La base del sitio, los orígenes de "
        "CORS y el bucket son configuración: entran por entorno y `HubOrganizacion` no tiene "
        "todavía columna para ellos, así que un literal aquí ata el código a un despliegue.\n"
        + "\n".join(encontrados)
    )


def test_el_despliegue_pasa_las_tres_variables_del_sitio() -> None:
    texto = _texto(DESPLIEGUE)
    for variable in ("CORPUS_SITE_BASE_URL", "CORS_ALLOWED_ORIGINS", "CORPUS_BUCKET"):
        assert re.search(rf"^\s*{variable}=\$\{{\{{ vars\.{variable} \}}\}}", texto, re.M), (
            f"`.env.despliegue` no recibe {variable} desde las variables del repositorio. Una "
            f"que falte no rompe el arranque: deja las citas donde estaban, o el preflight "
            f"rechazando al origen nuevo, y se descubre cuando alguien abre un enlace."
        )
