"""Lo que `server/app` importa está declarado, o es un extra con su guarda (DEP.1).

**Por qué existe, y cuánto costó no tenerlo.** DEP.1 sacó `browser-use` y `ragas` del conjunto
por defecto, y al hacerlo destapó **tres** paquetes que la aplicación usaba y nadie declaraba,
porque llegaban de rebote como transitivas suyas:

* `python-multipart` — lo exige FastAPI para `UploadFile`/`Form(`. Falla al *atender* la
  petición, no al importar: un 500 subiendo un PDF con el arranque en verde.
* `langchain` — lo necesita `observability.py`, que hace
  `from langfuse.langchain import CallbackHandler` en el nivel superior.
* `beautifulsoup4` — import de nivel superior en `html_analyzer_service.py` y en
  `normativa_spider.py`.

Y uno más que no rompía la importación pero sí una capacidad: `langchain-community`, que
sostiene el proveedor **Ollama** desde un import perezoso y sin guarda.

Los tres primeros se encontraron **de uno en uno, a golpe de suite roja**. Este guardarraíl los
habría dado los cuatro juntos y en segundos. La regla que fija es la que el empaquetado de
Python recomienda desde siempre: **se depende de lo que se importa**, no de lo que otro paquete
tenga a bien arrastrar.

**Lo que este test NO exige.** No obliga a declarar cada transitiva que se importe de pasada
—`sqlalchemy` por `sqlmodel`, `starlette` por `fastapi`, `numpy` por `pandas`—: ésa es otra
discusión y cambiarlo ahora sería ruido. Lo que exige es que **todo módulo importado se pueda
resolver**, o que su ausencia sea deliberada y esté en la lista de abajo con su motivo.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APP = RAIZ / "server" / "app"

#: Paquetes de primer nivel que la aplicación importa y que **a propósito** pueden faltar.
#: Cada uno vive en un extra y su consumidor degrada con un `try/except ImportError`.
#: Añadir algo aquí es una decisión: significa «esta capacidad es opcional y su ausencia está
#: manejada». Si el consumidor no la maneja, el sitio de la dependencia es el manifiesto.
AUSENCIAS_DELIBERADAS = {
    "browser_use": "extra `agente-navegador`; agent_service deja Agent = None",
    "ragas": "extra `evaluacion`; rag_metrics cae a la métrica léxica",
    "datasets": "extra `evaluacion`; sólo lo usa rag_metrics",
    "sentence_transformers": "extra `local-models`; el servicio dice qué instalar",
}

#: Nombres que no son paquetes de terceros.
PROPIOS = {"server", "app", "shared", "automatia_shared", "tests"}


def _modulos_importados() -> set[str]:
    """Los módulos de primer nivel que importa el árbol de la aplicación."""
    encontrados: set[str] = set()
    for py in APP.rglob("*.py"):
        try:
            arbol = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:  # pragma: no cover - no debería haberlos
            continue
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    encontrados.add(alias.name.split(".")[0])
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                encontrados.add(nodo.module.split(".")[0])
    return encontrados


def _de_terceros(modulos: set[str]) -> set[str]:
    return {
        m
        for m in modulos
        if m not in sys.stdlib_module_names and m not in PROPIOS and not m.startswith("_")
    }


def test_todo_lo_que_se_importa_se_puede_resolver() -> None:
    """Lo que no resuelve llega de rebote, y se rompe cuando su padre transitivo cambie."""
    huerfanos = sorted(
        m
        for m in _de_terceros(_modulos_importados())
        if m not in AUSENCIAS_DELIBERADAS and importlib.util.find_spec(m) is None
    )
    assert not huerfanos, (
        "Estos módulos se importan y no se pueden resolver con las dependencias instaladas: "
        f"{huerfanos}.\n"
        "O se declaran en `server/pyproject.toml` —si la aplicación los necesita— o se añaden "
        "a `AUSENCIAS_DELIBERADAS` con su motivo, y entonces su consumidor tiene que manejar "
        "la ausencia con un `try/except ImportError`. Lo que no vale es dejarlos llegando de "
        "rebote: el día que su padre transitivo cambie, se rompen sin que nada lo anuncie."
    )


def test_las_ausencias_deliberadas_siguen_siendo_ciertas() -> None:
    """Una exención que ya no aplica es una exención que tapa el próximo caso.

    Si un paquete de la lista pasa a estar siempre instalado, la lista miente y conviene
    quitarlo: la próxima vez que alguien lo saque, este test no dirá nada.
    """
    instalados = sorted(
        m for m in AUSENCIAS_DELIBERADAS if importlib.util.find_spec(m) is not None
    )
    assert not instalados, (
        f"{instalados} están en AUSENCIAS_DELIBERADAS y sin embargo están instalados en el "
        f"entorno base. O el entorno tiene extras que no debería —¿se sincronizó con "
        f"`--all-extras`?— o han vuelto a las dependencias base y la exención sobra."
    )


def test_los_importados_de_verdad_no_son_cuatro() -> None:
    """Que el recorrido mire de verdad: un árbol vacío pasaría los dos tests de arriba."""
    terceros = _de_terceros(_modulos_importados())
    assert len(terceros) >= 30, (
        f"Sólo se han encontrado {len(terceros)} módulos de terceros importados por "
        f"`server/app`. Eran 44 al escribir esto. Un recorrido que deja de encontrar ficheros "
        f"pasa en verde sin comprobar nada, y es la avería que este proyecto ya ha pagado."
    )
