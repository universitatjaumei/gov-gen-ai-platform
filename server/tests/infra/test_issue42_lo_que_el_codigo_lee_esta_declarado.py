"""Issue #42 — toda variable de entorno que lee el código está declarada en algún inventario.

Hay dos inventarios y cada uno responde a una pregunta distinta:

* **`.env.example`** dice **qué se puede configurar** y qué pasa si se deja en blanco. Es lo que
  lee quien instala esto por primera vez.
* **`scripts/lib/secretos.tsv`** dice **qué hay que crear y rotar** en el despliegue. Lo leen
  `gcp_create_secrets.sh` y `vm_fetch_secrets.sh`.

Una variable que el código lee y que no está en ninguno de los dos **no se crea al aprovisionar
y no se documenta a quien instala**. No es una brecha: es deriva entre el inventario y el código,
que es el tipo de cosa que la próxima vez sí abre algo.

**El caso que lo destapó.** `DELEGATED_ACTOR_SECRET` estaba en `.env.example` pero **no** en
`secretos.tsv`, y `delegated_actor.py` **falla cerrado** si falta. O sea que la actuación «en
nombre de» —que usan seis módulos— estaba muerta en el despliegue y el síntoma sólo aparecía
cuando alguien la usara. Fallar cerrado es lo correcto; lo que no lo es, es que nadie se entere.

**Y al medirlo salieron siete sin declarar, no seis.** La issue listaba `LOG_LEVEL`,
`DEV_ADMIN_EMAIL`, `DEV_ADMIN_PASSWORD`, `CRAWLER_CONTACT`, `SUPERADMIN_EMAIL` y
`SUPERADMIN_PASSWORD`; faltaba `SUPERADMIN_NAME`, que se lee en el mismo sitio que las otras dos.
De regalo, el docstring de `main.py` afirmaba que `LOG_LEVEL` «ya está en `.env.example`» y no
estaba: una frase que se escribió a la vez que la intención y nadie volvió a comprobar.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APP = RAIZ / "server" / "app"
ENV_EJEMPLO = RAIZ / ".env.example"
SECRETOS = RAIZ / "scripts" / "lib" / "secretos.tsv"

_LECTURA = re.compile(
    r"os\.(?:environ\.get|getenv)\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"
    r"|os\.environ\[\s*[\"']([A-Z][A-Z0-9_]*)[\"']"
)
_DECLARACION = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)=", re.MULTILINE)


def _leidas_por_el_codigo() -> dict[str, str]:
    """`{VARIABLE: primer fichero donde se lee}`."""
    encontradas: dict[str, str] = {}
    for fichero in APP.rglob("*.py"):
        if "__pycache__" in fichero.parts:
            continue
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        for coincidencia in _LECTURA.finditer(texto):
            nombre = coincidencia.group(1) or coincidencia.group(2)
            encontradas.setdefault(nombre, str(fichero.relative_to(RAIZ)))
    return encontradas


def _declaradas_en_el_ejemplo() -> set[str]:
    return set(_DECLARACION.findall(ENV_EJEMPLO.read_text(encoding="utf-8")))


def _declaradas_como_secreto() -> set[str]:
    nombres = set()
    for linea in SECRETOS.read_text(encoding="utf-8").splitlines():
        if linea.startswith("#") or "|" not in linea:
            continue
        variable = linea.split("|")[1]
        nombres.add(variable.removeprefix("FICHERO:"))
    return nombres


def test_el_codigo_no_lee_nada_que_no_este_declarado() -> None:
    leidas = _leidas_por_el_codigo()
    declaradas = _declaradas_en_el_ejemplo() | _declaradas_como_secreto()
    huerfanas = sorted(n for n in leidas if n not in declaradas)

    assert not huerfanas, (
        "El código lee variables que no declara ningún inventario:\n  - "
        + "\n  - ".join(f"{n}  (en {leidas[n]})" for n in huerfanas)
        + "\n\nUna variable que no está en `.env.example` no se la documenta a quien instala, y "
        "una que no está en `secretos.tsv` no se crea ni se rota al aprovisionar."
    )


def test_el_secreto_de_la_delegacion_se_crea_al_aprovisionar() -> None:
    """El caso concreto, con nombre, porque su síntoma es el peor: silencio.

    `delegated_actor.py` rechaza la cabecera si el secreto falta, que es lo correcto. Pero si el
    despliegue nunca lo crea, la funcionalidad está muerta y sólo se nota cuando alguien intenta
    usarla — y entonces parece un fallo de quien la usa.
    """
    assert "DELEGATED_ACTOR_SECRET" in _declaradas_como_secreto(), (
        "`DELEGATED_ACTOR_SECRET` no está en `secretos.tsv`, así que `gcp_create_secrets.sh` no "
        "lo crea y `vm_fetch_secrets.sh` no lo baja. La actuación «en nombre de» queda muerta en "
        "el despliegue sin que nada lo diga."
    )


def test_el_guardarrail_encuentra_algo_que_mirar() -> None:
    """Un test que cruza dos listas vacías pasa en verde sin comprobar nada.

    Se fijan cotas bajas a propósito: no son cifras que haya que mantener, son el mínimo por
    debajo del cual este fichero habría dejado de leer lo que cree leer.
    """
    assert len(_leidas_por_el_codigo()) >= 40, "apenas se ven lecturas de entorno en el código"
    assert len(_declaradas_en_el_ejemplo()) >= 40, "`.env.example` casi no declara nada"
    assert len(_declaradas_como_secreto()) >= 5, "`secretos.tsv` casi no declara nada"
