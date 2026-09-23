"""Los avisos que emite GitHub se revisan solos, y no cuando alguien se acuerda.

**De dónde sale.** El 2026-09-23, antes de abrir el repositorio, el mantenedor lo dijo así: «lo
voy viendo y te voy diciendo, pero si se me pasa o se me olvida se queda por revisar». Es la
descripción exacta de un control que existe y no actúa. Este proyecto ya tiene la lección escrita
—`docs/` la registra como «se cumple donde está mecanizado y se escapa donde sólo estaba
escrito»—, así que la respuesta no podía ser una línea más en `AGENTS.md`.

**Lo que ya estaba mecanizado, y por eso no se rehace.** El job `supply-chain` de `ci.yml` audita
los cinco locks en **cada** commit y bloquea; `avisos_aceptados.toml` es su única puerta de
salida, con cinco campos y caducidad; `test_dep7_las_aceptaciones_caducan.py` impide que esa
lista crezca en silencio. Nada de eso se duplica aquí: este workflow **reutiliza el mismo
fichero** de aceptaciones. Dos listas de exclusiones que dicen cosas distintas es peor que
ninguna.

**Lo que faltaba es todo lo que vive del lado de GitHub** y no se puede calcular desde el árbol:
las alertas de la pestaña Dependabot, las PR de actualización pendientes y los informes de
Copilot.

**Por qué las alertas se comprueban DESPUÉS de mezclar y no antes.** Dependabot calcula sus
alertas contra la **rama por omisión**, que aquí es `main`. Un arreglo que vive en `desarrollo`
no puede cerrarlas: seguirán abiertas hasta que se mezclen. Una puerta que bloqueara la PR por
«hay alertas abiertas» dejaría roja precisamente a la PR que las corrige, y un punto muerto se
resuelve siempre igual —desactivando la puerta—. Así que el reparto sigue a la física del dato:

* **Antes de mezclar** se comprueba lo que se puede calcular de la rama. Eso ya lo hace
  `supply-chain`, y aquí se añade lo que también es pre-merge por naturaleza: que los informes de
  Copilot estén atendidos.
* **Al mezclar a `main`** —que es cuando se despliega— se exige que **ninguna alerta quede sin
  decidir**: o corregida, o descartada en GitHub con motivo, o aceptada en
  `avisos_aceptados.toml` con firma y fecha de caducidad.

**Y los hilos de Copilot se comprueban con un disparador propio.** Copilot comenta cuando
termina, que suele ser después de que CI haya pasado. Un control que sólo corriera con el `push`
daría verde antes de que existiera el comentario, y nadie volvería a mirarlo: por eso el
workflow escucha también `pull_request_review` y `pull_request_review_comment`. Es la diferencia
entre comprobar y haber comprobado en el único instante en que no había nada que ver.

**La propiedad que este fichero defiende por encima de las demás**: que el workflow distinga
**«no pude mirar» de «no hay nada»**. Si la API de alertas responde 403 —y puede, porque el
alcance del token de Actions sobre Dependabot no es el mismo en todos los repositorios—, el paso
tiene que ponerse rojo, no reportar cero. Este proyecto ya se comió un guardarraíl que recorría
un directorio inexistente y pasaba en verde, y la lección quedó escrita: **un medidor que no mira
nada pasa en verde**.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
WORKFLOW = RAIZ / ".github" / "workflows" / "avisos.yml"


@pytest.fixture(scope="module")
def texto() -> str:
    assert WORKFLOW.is_file(), (
        f"Falta {WORKFLOW.relative_to(RAIZ).as_posix()}. Es lo único que revisa los avisos que "
        f"GitHub emite y que no se pueden calcular desde el árbol: alertas de Dependabot, PR de "
        f"actualización pendientes e informes de Copilot."
    )
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def datos(texto: str) -> dict:
    return yaml.safe_load(texto)


def _disparadores(datos: dict) -> dict:
    # PyYAML lee el `on:` de un workflow como el booleano True, que es la trampa clásica de YAML
    # 1.1. Si algún día se arregla en la biblioteca, la clave literal sigue valiendo.
    return datos.get(True) or datos.get("on") or {}


def test_el_medidor_lee_el_workflow(datos: dict) -> None:
    # Sin esto, un `on:` que PyYAML no encontrara dejaría en verde a todos los test de abajo
    # comparando listas vacías contra listas vacías.
    assert _disparadores(datos), (
        "no se han podido leer los disparadores del workflow; los test que comprueban cuándo "
        "corre estarían comparando nada contra nada"
    )


def test_las_alertas_se_revisan_al_desplegar(datos: dict) -> None:
    ramas = (_disparadores(datos).get("push") or {}).get("branches") or []
    assert "main" in ramas, (
        "el workflow no corre al empujar a `main`. Las alertas de Dependabot se calculan contra "
        "la rama por omisión, así que ése es el primer instante en que la foto es cierta — y "
        "coincide con el despliegue, que es cuando se pidió la revisión."
    )


def test_los_informes_de_copilot_se_revisan_antes_de_mezclar(datos: dict) -> None:
    disparadores = _disparadores(datos)
    assert "pull_request" in disparadores, "el workflow no corre en las PR"

    faltan = [
        evento
        for evento in ("pull_request_review", "pull_request_review_comment")
        if evento not in disparadores
    ]
    assert not faltan, (
        f"el workflow no escucha {faltan}. Copilot comenta cuando termina, normalmente después "
        f"de que CI haya pasado: sin estos disparadores el control daría verde en el único "
        f"instante en que todavía no había nada que ver, y no volvería a ejecutarse."
    )


def test_hay_una_revision_periodica(datos: dict) -> None:
    assert _disparadores(datos).get("schedule"), (
        "no hay `schedule`. Una alerta puede aparecer un martes sin que nadie toque el "
        "repositorio en dos semanas, y entonces ningún disparador por evento la vería."
    )


def test_declara_permisos_y_no_pide_escritura(datos: dict) -> None:
    # APER.8 ya exige `permissions` en la raíz de todo workflow; esto lo repite en corto para que
    # el fallo señale a este fichero y no a un test genérico.
    permisos = datos.get("permissions")
    assert permisos, "el workflow no declara `permissions` en la raíz"
    escrituras = [k for k, v in permisos.items() if v == "write"]
    assert not escrituras, (
        f"el workflow pide escritura en {escrituras}. Sólo lee avisos: no tiene por qué poder "
        f"cambiar nada."
    )


def test_reutiliza_el_fichero_de_aceptaciones(texto: str) -> None:
    assert "avisos_aceptados.toml" in texto, (
        "el workflow no lee `avisos_aceptados.toml`. Ése es el sitio donde este proyecto decide "
        "qué aviso se acepta y hasta cuándo, con los cinco campos que vigila DEP.7. Inventar "
        "aquí una segunda lista de exclusiones dejaría dos fuentes que se contradicen, y la "
        "que caduca es la que perdería."
    )


def test_no_mirar_no_es_no_haber_nada(texto: str) -> None:
    """La llamada a la API de alertas tiene que tener su rama de error, y tiene que ser roja."""
    llamada = re.search(
        r"^(?P<sangria>\s*)if\s+!\s+[A-Z_]+=\"\$\(gh api [^\n]*dependabot/alerts",
        texto,
        re.MULTILINE,
    )
    assert llamada, (
        "no se encuentra la llamada a `dependabot/alerts` protegida por un `if !`. Si la API "
        "responde 403 —y puede, porque el alcance del token de Actions sobre Dependabot no es "
        "igual en todos los repositorios—, un `gh api` sin comprobar deja la lista vacía y el "
        "paso pasa en verde diciendo que no hay alertas. Es el modo de fallo que este proyecto "
        "ya vio: un medidor que no mira nada pasa en verde."
    )

    # Y la rama de error tiene que terminar el paso, no sólo avisar.
    despues = texto[llamada.end() : llamada.end() + 900]
    assert "::error::" in despues and "exit 1" in despues, (
        "la llamada a `dependabot/alerts` está protegida, pero su rama de error no pone el paso "
        "en rojo. Un aviso en el log que no falla el job es indistinguible de no haberlo mirado."
    )


def test_ninguna_llamada_a_avisos_se_silencia(texto: str) -> None:
    silenciadas = [
        linea.strip()
        for linea in texto.splitlines()
        if "gh api" in linea and ("|| true" in linea or "2>/dev/null" in linea)
    ]
    assert not silenciadas, (
        f"hay llamadas a la API con el error silenciado: {silenciadas}. Un fallo tragado aquí se "
        f"lee exactamente igual que «no hay avisos»."
    )
