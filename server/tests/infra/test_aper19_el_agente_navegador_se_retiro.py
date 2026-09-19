"""APER.19 — retirado el agente de navegador, y con él tres avisos de seguridad.

**Por qué se va.** `browser-use` lo importaba **un solo fichero**, `services/agent_service.py`, y
a ése no lo llamaba nadie en producción: sólo `test_imports.py` y un guardarraíl de dependencias.
Es el hallazgo **M7** de la auditoría del 2026-08-10 —«tres servicios sin llamantes de
producción»— que seguía abierto.

**Y lo que costaba tenerlo.** El extra `agente-navegador` arrastraba `authlib`, `httplib2` y
`mcp`, que eran **tres de los seis avisos de seguridad** abiertos el 2026-09-19, uno de ellos
crítico. Retirar el extra los quita **de raíz**: no se actualiza nada, se deja de depender. Es la
misma forma que APER.12, donde `pdfplumber` traía `pillow` y diecinueve avisos desaparecieron al
borrar el código muerto que lo pedía.

**Lo que NO se va, comprobado antes de borrar.** `python-multipart` llega también por
`browser-use → mcp`, y la aplicación lo necesita para `UploadFile` y `Form`. Está declarado
**directamente** en el manifiesto desde DEP.1, así que las subidas no dependen de este extra —se
verificó en el conjunto desplegado antes de tocar nada—. Lo mismo con `openai` y `google-genai`,
que son dependencias directas del servidor, y con `pillow` y `click`, que llegan por
`camelot-py`, `matplotlib` y `typer`.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
MANIFIESTO = RAIZ / "server" / "pyproject.toml"
LOCK = RAIZ / "server" / "uv.lock"


@pytest.fixture(scope="module")
def manifiesto() -> dict:
    return tomllib.loads(MANIFIESTO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lock() -> str:
    return LOCK.read_text(encoding="utf-8")


class TestElExtraYaNoExiste:

    def test_el_manifiesto_no_declara_el_extra(self, manifiesto: dict) -> None:
        extras = manifiesto["project"].get("optional-dependencies", {})
        assert "agente-navegador" not in extras, (
            "El extra `agente-navegador` sigue declarado. Traía `authlib`, `httplib2` y `mcp` "
            "—tres avisos de seguridad— para un servicio sin llamantes."
        )

    def test_nadie_declara_browser_use(self, manifiesto: dict) -> None:
        texto = MANIFIESTO.read_text(encoding="utf-8")
        declaraciones = [
            linea for linea in texto.splitlines()
            if "browser-use" in linea and not linea.lstrip().startswith("#")
        ]
        assert not declaraciones, f"`browser-use` sigue declarado: {declaraciones}"

    def test_el_servicio_se_borro(self) -> None:
        """Se retira **borrando**: el historial de git es la fuente de verdad del pasado."""
        assert not (RAIZ / "server" / "app" / "services" / "agent_service.py").exists(), (
            "`agent_service.py` sigue ahí. Es el único importador de `browser_use` y no tiene "
            "llamantes de producción."
        )


class TestNadieLoImporta:

    def test_ningun_fichero_importa_browser_use(self) -> None:
        culpables = []
        for base in ("app", "tests", "scripts"):
            raiz = RAIZ / "server" / base
            if not raiz.is_dir():
                continue
            for fichero in raiz.rglob("*.py"):
                if "__pycache__" in fichero.parts:
                    continue
                for linea in fichero.read_text(encoding="utf-8", errors="replace").splitlines():
                    desnuda = linea.lstrip()
                    if desnuda.startswith(("import browser_use", "from browser_use")):
                        culpables.append(f"{fichero.relative_to(RAIZ)}: {desnuda}")
        assert not culpables, f"Todavía se importa `browser_use`: {culpables}"

    def test_nadie_referencia_el_servicio(self) -> None:
        culpables = []
        for base in ("app", "tests", "scripts"):
            raiz = RAIZ / "server" / base
            if not raiz.is_dir():
                continue
            for fichero in raiz.rglob("*.py"):
                if "__pycache__" in fichero.parts or fichero.name.startswith("test_aper19"):
                    continue
                texto = fichero.read_text(encoding="utf-8", errors="replace")
                if "services.agent_service" in texto or "BrowserAgentWrapper" in texto:
                    culpables.append(str(fichero.relative_to(RAIZ)))
        assert not culpables, (
            f"Estos ficheros siguen referenciando el servicio retirado: {culpables}. "
            "«Migración completa» incluye quitar los imports (checklist de AGENTS.md)."
        )


class TestLosTresAvisosSeVanConEl:
    """Lo que hacía que esto mereciera la pena, comprobado sobre el lock."""

    @pytest.mark.parametrize("paquete", ["authlib", "httplib2", "browser-use"])
    def test_el_paquete_ya_no_esta_en_el_lock(self, lock: str, paquete: str) -> None:
        assert f'name = "{paquete}"\n' not in lock, (
            f"`{paquete}` sigue en el lock de `server`. Entraba por `browser-use`, y era uno de "
            "los avisos que esta retirada quita de raíz."
        )

    def test_mcp_solo_sobrevive_si_alguien_mas_lo_pide(self, lock: str) -> None:
        """`mcp` también lo usa el proyecto `mcp_server`, que tiene su propio lock.

        Aquí se comprueba el lock **del servidor**: si `mcp` sigue, es que algo más lo pide y
        hay que mirarlo, no darlo por bueno.
        """
        assert 'name = "mcp"\n' not in lock, (
            "`mcp` sigue en el lock del servidor. Venía por `browser-use`; si ahora lo pide otra "
            "cosa, hay que decir cuál."
        )


class TestLoQueNoSeVa:
    """Lo que se comprobó **antes** de borrar, y que un descuido futuro podría llevarse."""

    def test_python_multipart_sigue_declarado(self, manifiesto: dict) -> None:
        """Llegaba también por `browser-use → mcp`, y la aplicación lo necesita para las subidas.

        Está declarado directamente desde DEP.1, que es lo que hace segura esta retirada. Si
        alguien lo quita creyendo que sobra, `UploadFile` y `Form` dejan de funcionar.
        """
        directas = " ".join(manifiesto["project"]["dependencies"])
        assert "python-multipart" in directas, (
            "`python-multipart` ha dejado de declararse. Venía también por `browser-use → mcp`, "
            "así que sin la declaración directa las subidas se rompen."
        )

    @pytest.mark.parametrize("paquete", ["openai", "google-genai", "pillow", "click"])
    def test_lo_que_llegaba_por_otras_vias_sigue(self, lock: str, paquete: str) -> None:
        """No todo lo que tocaba `browser-use` era suyo: esto lo piden otros."""
        assert f'name = "{paquete}"\n' in lock, (
            f"`{paquete}` ha desaparecido del lock. Llegaba también por otra vía —`openai` y "
            "`google-genai` son dependencias directas; `pillow` viene por `camelot-py` y "
            "`matplotlib`; `click` por `typer`— así que perderlo es un efecto no buscado."
        )
