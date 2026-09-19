"""Issue #41 — el enlace al fuente del §13 se puede configurar **en el despliegue real**.

**Casi toda esta issue ya estaba hecha, y el que iba por detrás era el documento.** El endpoint
`GET /api/v1/instancia` existe desde AIS.6, y el componente `EnlaceAlFuente` lo consume **en los
dos sitios** —el pie del panel (`AppLayout.tsx`) y el pie del widget embebido
(`ChatWidget.tsx`)— desde `6fb4281a`, con tests de los dos caminos: con `SOURCE_URL` puesta se
pinta el enlace, vacía no se pinta nada. Lo que seguía diciendo lo contrario era el `README`:
«lo que falta es que se vea: ninguna interfaz lo consume todavía». Y no es una imprecisión
cualquiera, porque afirma que un despliegue **incumple** una obligación de licencia que sí
cumple.

**Lo que sí faltaba, y no estaba en la issue.** Se vio preguntándole a producción:
`https://normativa.uji.es/api/v1/instancia` devuelve `{"source_url": null}`. No porque nadie
haya querido ponerla, sino porque **no hay por dónde**: la configuración no secreta del
contenedor entra por el bloque `environment:` de `deploy/vm/docker-compose.vm.yml`, que se
rellena desde `.env.despliegue`, y `SOURCE_URL` no estaba en ninguno de los dos. El
`.env.runtime` tampoco vale: ése lo escribe `vm_fetch_secrets.sh` y sólo lleva lo que hay en
`secretos.tsv`, o sea secretos de Secret Manager.

O sea: la interfaz sabe enseñar el enlace, el servidor sabe servirlo, y **quien despliega un
fork no tiene forma de ponerlo**. Es la misma avería que APER.22 —una capacidad construida y un
interruptor que no llega a ella— y el mismo motivo por el que la issue estaba en el hito «antes
de abrir»: quien tome esto de plantilla y modifique el código necesita poder cumplir el §13.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE_VM = RAIZ / "deploy" / "vm" / "docker-compose.vm.yml"
DEPLOY = RAIZ / ".github" / "workflows" / "deploy.yml"
README = RAIZ / "README.md"


def test_el_contenedor_recibe_la_variable() -> None:
    """Sin esto, `SOURCE_URL` no llega al proceso por mucho que se configure."""
    datos = yaml.safe_load(COMPOSE_VM.read_text(encoding="utf-8"))
    entorno = (datos["services"]["app"] or {}).get("environment") or {}
    assert "SOURCE_URL" in entorno, (
        "El servicio `app` del compose de la VM no recibe `SOURCE_URL`. La configuración no "
        "secreta entra por aquí; el `.env.runtime` sólo lleva lo de `secretos.tsv`. Sin esta "
        "línea, el endpoint devuelve siempre vacío y el enlace del §13 no se puede enseñar."
    )
    valor = str(entorno["SOURCE_URL"])
    assert ":?" not in valor, (
        f"`SOURCE_URL: {valor}` es obligatoria, y no puede serlo: vacía significa «sin enlace», "
        "que es lo correcto para quien despliega el código sin modificar. Exigirla sería "
        "inventarse un requisito que la licencia no pone."
    )


def test_el_despliegue_la_escribe_en_la_configuracion() -> None:
    """Y que salga de una variable del repositorio, no de una constante en el workflow."""
    texto = DEPLOY.read_text(encoding="utf-8")
    linea = next(
        (l for l in texto.splitlines() if l.strip().startswith("SOURCE_URL=")), None
    )
    assert linea is not None, (
        "`deploy.yml` no escribe `SOURCE_URL` en `.env.despliegue`, así que el compose nunca la "
        "ve. Es donde se rellenan las demás: host, bucket, proyecto, orígenes CORS."
    )
    assert "vars." in linea, (
        f"«{linea.strip()}» no sale de una variable del repositorio. El §13 pide el fuente **de "
        "esa versión**: una constante apuntaría al principal y cualquier fork modificado "
        "incumpliría creyendo que cumple."
    )


def test_el_readme_ya_no_dice_que_ninguna_interfaz_lo_consume() -> None:
    """La frase afirmaba que se incumple una obligación de licencia que sí se cumple."""
    texto = README.read_text(encoding="utf-8")
    seccion = re.search(
        r"### La obligación del §13 sobre cada despliegue(.*?)(?=\n## |\n### |\Z)",
        texto,
        re.DOTALL,
    )
    assert seccion, "ha desaparecido la sección del §13 del README"
    cuerpo = seccion.group(1)
    for frase in ("Hecho a medias", "ninguna interfaz lo consume"):
        assert frase not in cuerpo, (
            f"el README sigue diciendo «{frase}». El panel y el widget lo consumen desde "
            "`6fb4281a`, con tests de los dos caminos: decir que no es afirmar que este "
            "despliegue incumple el §13 cuando no es verdad."
        )
