"""Lo que la aplicación usa está declarado, y lo que no usa no se instala (DEP.1).

Tres afirmaciones, y las tres nacen de la primera medición del job `supply-chain`
(2026-09-08). La primera es un defecto latente y las otras dos son la premisa que permite
arreglarlo sin tocar código.

* **`python-multipart` tiene que estar DECLARADO.** Hoy llega por
  `browser-use → mcp → python-multipart`, y la aplicación lo necesita: `UploadFile` y `Form(`
  aparecen 22 veces en 7 ficheros. FastAPI **no falla al importar** por esto — falla al
  *atender* la petición, así que el síntoma sería un 500 subiendo un PDF en producción con el
  arranque en verde. Se comprueba que está en el manifiesto, no que esté instalado: instalado
  está hoy, y ése es justamente el problema.

* **`browser-use` y `ragas` degradan de verdad cuando faltan.** Los dos importan dentro de un
  `try/except ImportError` y ésa es la razón de que se puedan sacar del conjunto por defecto.
  Aquí no se supone: se bloquea el import y se comprueba que el mecanismo de reserva entra.
  Si alguien convierte esos imports en incondicionales, este test se pone rojo antes de que
  el despliegue se caiga al arrancar.

* **El despliegue no instala los extras.** Si la imagen los instalara igualmente, el ejercicio
  no habría servido de nada y el árbol de dependencias seguiría igual de grande.
"""

from __future__ import annotations

import importlib
import sys
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
MANIFIESTO = RAIZ / "server" / "pyproject.toml"
DOCKERFILE = RAIZ / "Dockerfile"

#: Los extras que DEP.1 crea. Ninguno debe instalarse en el despliegue estándar.
#:
#: `agente-navegador` estuvo aquí y lo retiró **APER.19**: su `browser-use` lo pedía un solo
#: fichero sin llamantes de producción, y traía `authlib`, `httplib2` y `mcp` —tres avisos de
#: seguridad, uno crítico—. La idea de DEP.1 no cambia; lo que desaparece es uno de sus dos
#: ejemplos.
EXTRAS_OPCIONALES = ("evaluacion",)


@pytest.fixture(scope="module")
def manifiesto() -> dict:
    assert MANIFIESTO.is_file(), f"Falta {MANIFIESTO.relative_to(RAIZ).as_posix()}"
    return tomllib.loads(MANIFIESTO.read_text(encoding="utf-8"))


def _nombres(dependencias: list[str]) -> set[str]:
    """`fastapi>=0.111.0` → `fastapi`. Normaliza guiones y mayúsculas como hace PyPI."""
    limpios = set()
    for d in dependencias:
        nombre = d.split(";")[0].split("[")[0]
        for sep in (">=", "<=", "==", "~=", "!=", ">", "<"):
            nombre = nombre.split(sep)[0]
        limpios.add(nombre.strip().lower().replace("_", "-"))
    return limpios


class TestLoQueSeUsaEstaDeclarado:
    def test_python_multipart_esta_en_el_manifiesto(self, manifiesto: dict) -> None:
        declaradas = _nombres(manifiesto["project"]["dependencies"])
        assert "python-multipart" in declaradas, (
            "`python-multipart` no está declarado y la aplicación lo necesita: FastAPI lo exige "
            "para procesar `UploadFile` y `Form(`, que se usan en ingestión, subidas, "
            "workspaces, scripts, borradores y temas. Hoy llega por casualidad, como "
            "transitiva de `browser-use → mcp`. El día que ese árbol cambie, la subida de un "
            "PDF empieza a dar 500 en producción **sin que el arranque falle**, que es la peor "
            "forma de enterarse."
        )

    def test_hay_modulos_que_lo_necesitan(self) -> None:
        """El test de arriba no vale de nada si nadie usa `UploadFile`: sería una regla huérfana."""
        app = RAIZ / "server" / "app"
        usuarios = [
            p.relative_to(RAIZ).as_posix()
            for p in app.rglob("*.py")
            if "UploadFile" in p.read_text(encoding="utf-8", errors="ignore")
        ]
        assert len(usuarios) >= 5, (
            f"Sólo {len(usuarios)} módulos usan `UploadFile`. Si de verdad ha dejado de usarse, "
            f"la dependencia sobra y este fichero entero hay que revisarlo; mientras se use, "
            f"tiene que estar declarada. Encontrados: {usuarios}"
        )


class TestLosOpcionalesDegradanDeVerdad:
    """Se bloquea el import y se comprueba la reserva. Es la premisa de sacarlos a extras."""

    @staticmethod
    def _sin(nombres: tuple[str, ...], modulo: str):
        """Recarga `modulo` con `nombres` inaccesibles, y deja `sys.modules` como estaba."""

        class Bloqueador:
            def find_module(self, fullname, path=None):  # pragma: no cover - API vieja
                return None

            def find_spec(self, fullname, path=None, target=None):
                if fullname in nombres or fullname.split(".")[0] in nombres:
                    raise ImportError(f"bloqueado a propósito por el test: {fullname}")
                return None

        previos = {n: sys.modules.pop(n, None) for n in list(sys.modules) if n.split(".")[0] in nombres}
        previo_modulo = sys.modules.pop(modulo, None)
        bloqueador = Bloqueador()
        sys.meta_path.insert(0, bloqueador)
        try:
            return importlib.import_module(modulo)
        finally:
            sys.meta_path.remove(bloqueador)
            for n, m in previos.items():
                if m is not None:
                    sys.modules[n] = m
            if previo_modulo is not None:
                sys.modules[modulo] = previo_modulo
            else:
                sys.modules.pop(modulo, None)

    # `test_agent_service_deja_agent_a_none_sin_browser_use` estuvo aquí y se fue con su
    # servicio en APER.19. Comprobaba que `agent_service` degradaba sin `browser_use`; ahora no
    # hay ni servicio ni extra que degradar, y lo que vigila que no vuelvan es
    # `test_aper19_el_agente_navegador_se_retiro.py`.

    def test_rag_metrics_cae_a_la_metrica_lexica_sin_ragas(self) -> None:
        modulo = self._sin(
            ("ragas", "datasets"), "server.app.modules.agents_hub.evaluation.rag_metrics"
        )
        assert modulo._RAGAS_AVAILABLE is False, (
            "`rag_metrics` tiene que caer a la métrica léxica cuando falta RAGAS. Su propia "
            "docstring dice que la evaluación es «a mano o de noche, jamás bloqueando un PR»: "
            "por eso puede vivir en un extra."
        )


class TestElDespliegueNoInstalaLosExtras:
    def test_el_dockerfile_no_pide_extras(self) -> None:
        texto = DOCKERFILE.read_text(encoding="utf-8")
        lineas = [linea for linea in texto.splitlines() if "uv sync" in linea]
        assert lineas, "No se encuentra la línea de instalación en el Dockerfile de la raíz."
        instalacion = " ".join(lineas)
        assert "--all-extras" not in instalacion, (
            "El Dockerfile no puede instalar `--all-extras`: metería de vuelta la pila de "
            "modelos locales y los extras que DEP.1 acaba de sacar, y el ejercicio no habría "
            "servido de nada."
        )
        for extra in EXTRAS_OPCIONALES:
            assert f"--extra {extra}" not in instalacion, (
                f"El Dockerfile instala `--extra {extra}`. Ese extra existe para NO estar en el "
                f"despliegue estándar; si un caso lo necesita, se documenta y se decide, no se "
                f"añade en silencio."
            )

    def test_los_extras_existen_y_llevan_lo_previsto(self, manifiesto: dict) -> None:
        extras = manifiesto["project"].get("optional-dependencies", {})
        for nombre in EXTRAS_OPCIONALES:
            assert nombre in extras, (
                f"Falta el extra `{nombre}`. DEP.1 saca del conjunto por defecto lo que la "
                f"aplicación no necesita para funcionar, pero **no retira la capacidad**: se "
                f"instala con `uv sync --extra {nombre}`."
            )
        assert {"ragas", "datasets"} <= _nombres(extras["evaluacion"])

    def test_los_opcionales_no_siguen_en_el_conjunto_por_defecto(self, manifiesto: dict) -> None:
        base = _nombres(manifiesto["project"]["dependencies"])
        # `browser-use` ya no está en ninguna parte (APER.19), así que aquí quedan los de
        # `evaluacion`. Se comprueba igual: declarar algo en un extra y dejarlo también en la
        # base no quita nada, porque se instala igual.
        for paquete in ("ragas", "datasets"):
            assert paquete not in base, (
                f"`{paquete}` sigue en las dependencias base. Declararlo en un extra y dejarlo "
                f"también aquí no quita nada: se instala igual."
            )
