"""AIS.3 — Las dependencias van en una dirección, y la que faltaba por vigilar es la de vuelta.

`CONTRIBUTING.md` §5 regula que **un módulo no importe de otro módulo**. La dirección inversa
—`core/` importando de `modules/` o, peor, de `routers/`— **no estaba regulada ni testada**, y la
auditoría del 2026-08-24 encontró 14 sitios, dos de ellos desde `routers/`.

Por qué importa, más allá de la simetría: `core/` es la capa que un fork menos va a querer tocar
—autenticación, tenencia, almacenamiento, ámbito—. Si arrastra `routers.redaccion`, cualquier
cambio en el router de un módulo pasa a ser un cambio potencial de la autenticación de todos, y el
`core` deja de poder leerse como base estable.

**Tres reglas, con tres severidades distintas, y la diferencia es deliberada:**

1. `core/` **nunca** importa de `routers/`. Sin excepciones y sin lista: es la jerarquía al revés
   y AIS.3 dejó los dos casos en cero.
2. `core/` importa de `modules/` sólo lo que ya importaba, y **la lista sólo puede encoger**. No
   se pone a cero porque lo que trae son los **modelos ORM**, que viven en el módulo que los
   posee; sacarlos a `core` es una migración de otro tamaño y no un arreglo de dirección.
3. Un módulo importa de otro sólo según la lista declarada. `agents_hub` **es de facto la capa
   base compartida** —ORM, `ConfigProvider`, `model_factory`, embeddings— y aquí se declara como
   tal en vez de fingir que la regla se cumple.

El trinquete es el mismo patrón de SEC.9.5: lo heredado se escribe y se congela, lo nuevo se
rechaza. Una lista que sólo puede encoger es una deuda que se ve; una regla sin test es una que
se olvida.
"""
from __future__ import annotations

import re
from pathlib import Path

_APP = Path("app")
_IMPORT = re.compile(r"^\s*(?:from|import)\s+(server\.app\.[\w.]+)", re.MULTILINE)


def _imports_de(directorio: Path) -> dict[Path, set[str]]:
    """Los módulos de `server.app.*` que importa cada fichero del directorio."""
    salida: dict[Path, set[str]] = {}
    for ruta in sorted(directorio.rglob("*.py")):
        if "__pycache__" in ruta.parts:
            continue
        encontrados = set(_IMPORT.findall(ruta.read_text(encoding="utf-8")))
        if encontrados:
            salida[ruta] = encontrados
    return salida


def _modulo_de(destino: str) -> str | None:
    """`server.app.modules.curation.spider` → `curation`."""
    partes = destino.split(".")
    if len(partes) >= 4 and partes[2] == "modules":
        return partes[3]
    return None


# ───────────────────────── Los trinquetes ─────────────────────────

#: Lo que `core/` importa hoy de `modules/`, con su razón. **Sólo puede encoger.**
#:
#: Todo lo que queda son **modelos ORM y la base declarativa**: viven en el módulo que los posee
#: y sacarlos a `core` es una migración de esquema conceptual, no un arreglo de dirección. Se
#: congela para que la lista no crezca mientras nadie decide moverlos.
_CORE_PUEDE_IMPORTAR = {
    "server.app.modules.agents_hub.database.config_models",
    "server.app.modules.agents_hub.database.operational_models",
    # El cliente de sandbox dibuja gráficos y valida el contrato del pipeline. Es el candidato
    # más claro a mudarse: `sandbox_client` es infraestructura y `chart_renderer` también.
    "server.app.modules.redaccion.services.charts.chart_renderer",
    "server.app.modules.redaccion.pipelines.contracts",
}

#: Qué módulo puede importar de qué otro, y por qué.
#:
#: `agents_hub` no importa de nadie, y eso no es casualidad: **es la capa base**. Tiene la base
#: declarativa (`HubOperationalBase`), los modelos operacionales que comparten curación e
#: informes, el `ConfigProvider` y el `model_factory`. Declararlo aquí es más honesto que repetir
#: que «los módulos no se importan entre sí» mientras 24 imports dicen lo contrario.
_MODULO_PUEDE_IMPORTAR = {
    "curation": {"agents_hub"},
    "redaccion": {"agents_hub"},
    "automation": set(),
    "agents_hub": set(),
}


class TestElNucleoNoDependeDeLaCapaHttp:

    def test_should_never_import_a_router_from_core(self):
        culpables = [
            f"{ruta.as_posix()} → {destino}"
            for ruta, destinos in _imports_de(_APP / "core").items()
            for destino in sorted(destinos)
            if destino.startswith("server.app.routers")
        ]

        assert culpables == [], (
            "core/ importando de routers/ es la jerarquía al revés: la autenticación pasa a "
            "depender de la capa HTTP de un módulo, y core deja de poder leerse como base "
            "estable.\n  " + "\n  ".join(culpables)
        )


class TestElNucleoSoloArrastraLoQueYaArrastraba:

    def test_should_not_grow_what_core_imports_from_modules(self):
        actuales = {
            destino
            for destinos in _imports_de(_APP / "core").values()
            for destino in destinos
            if destino.startswith("server.app.modules")
        }
        nuevos = sorted(actuales - _CORE_PUEDE_IMPORTAR)

        assert nuevos == [], (
            "core/ ha empezado a importar de modules/ algo que no importaba. La lista es una "
            "deuda heredada que sólo puede encoger, no un sitio donde apuntar dependencias "
            "nuevas:\n  " + "\n  ".join(nuevos)
        )

    def test_should_shrink_the_list_when_something_stops_being_imported(self):
        """Una entrada que ya no corresponde a nada tapa el hueco que dejó."""
        actuales = {
            destino
            for destinos in _imports_de(_APP / "core").values()
            for destino in destinos
            if destino.startswith("server.app.modules")
        }
        sobran = sorted(_CORE_PUEDE_IMPORTAR - actuales)

        assert sobran == [], (
            f"estas entradas ya no las importa nadie desde core/: {sobran}. Quítalas: una "
            "lista de excepciones que no se poda acaba permitiendo lo que ya nadie necesita."
        )


class TestUnModuloNoTiraDeOtroSinDeclararlo:

    def test_should_only_import_the_declared_modules(self):
        culpables: list[str] = []
        for nombre, permitidos in _MODULO_PUEDE_IMPORTAR.items():
            directorio = _APP / "modules" / nombre
            if not directorio.is_dir():
                continue
            for ruta, destinos in _imports_de(directorio).items():
                for destino in sorted(destinos):
                    otro = _modulo_de(destino)
                    if otro is None or otro == nombre or otro in permitidos:
                        continue
                    culpables.append(f"{ruta.as_posix()} → {destino}")

        assert culpables == [], (
            "estos módulos se importan entre sí sin estar declarado en "
            "_MODULO_PUEDE_IMPORTAR:\n  " + "\n  ".join(culpables)
        )

    def test_should_keep_the_base_layer_independent(self):
        """`agents_hub` es la capa base: si empieza a importar de otro módulo, deja de serlo y
        las dos listas de arriba se vuelven mentira."""
        culpables = [
            f"{ruta.as_posix()} → {destino}"
            for ruta, destinos in _imports_de(_APP / "modules" / "agents_hub").items()
            for destino in sorted(destinos)
            if (_modulo_de(destino) or "agents_hub") != "agents_hub"
        ]

        assert culpables == [], (
            "agents_hub importa de otro módulo:\n  " + "\n  ".join(culpables)
        )


class TestElModuloDeAutomatizacionSigueSinConsumidor:
    """AIS.3 no lo borra, lo **deja probado**.

    `modules/automation/` son 1.401 líneas sin un solo importador vivo: era el destino de la
    migración de `AIBrainService`, y la retirada de `api/v1/automation.py` en ROL.1 le quitó los
    endpoints sin darle otros. Borrarlo aquí sería borrar 1.400 líneas a ojo a mitad de un bloque
    de aislamiento, y el proyecto ya tiene un sitio para eso con el procedimiento correcto: el
    **Bloque NIC**, cuyo primer prompt no borra nada sino que cruza qué está cubierto — porque
    «borrar ficheros a ojo es como se pierde una funcionalidad sin enterarse».

    Lo que hace este test es que el dato no se pierda: si algún día alguien lo cablea, se entera
    aquí; y mientras tanto queda escrito que no lo consume nadie.
    """

    def test_should_have_no_live_importer(self):
        importadores = [
            ruta.as_posix()
            for ruta, destinos in _imports_de(_APP).items()
            if "modules/automation" not in ruta.as_posix()
            and any(d.startswith("server.app.modules.automation") for d in destinos)
        ]

        assert importadores == [], (
            "modules/automation ha ganado un consumidor: "
            f"{importadores}. Actualiza este test y sácalo del inventario del Bloque NIC, "
            "porque deja de ser código muerto."
        )
