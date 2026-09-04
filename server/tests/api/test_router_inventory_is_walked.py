"""SEC.9.5 — El inventario de routers se recorre; no es una lista que alguien recuerde ampliar.

**Por qué existe este fichero.** Los cuatro agujeros que abrió SEC.9 —`library_router` sin
autenticar, `hub_llm_configs` y `hub_activity_prompts` sin tenencia, la subida sin límite de
`llm-drafts`— estaban precisamente **donde el gate no miraba**:

- El paso «Access control gate» de `ci.yml` ejecuta una lista de ficheros de test escrita a mano,
  y no incluía ninguno de los routers añadidos en los bloques REV y MT.
- El guardarraíl de `test_tenant_isolation.py` recorre una tupla de nueve nombres y hace
  `if not ruta.is_file(): continue`, así que un nombre mal escrito —había uno, `hub_feedback_router.py`,
  que vive en `api/v1/`— se salta **en silencio**.
- El inventario de módulos de `test_plat5_frontera_de_modulos.py` se valida sobre **docstrings**.
  `library_router` decía «Módulo: plataforma» en el suyo y no tenía ninguna dependencia: el check
  pasaba en verde sobre un router abierto de par en par.

El patrón bueno ya estaba en el proyecto: `tablas_sin_ambito()` (MT.1) recorre el registro de
modelos, así que una tabla nueva pone rojo el guardarraíl sin que nadie la añada a nada. Esto es lo
mismo para los routers: **se descubren recorriendo el árbol**, y lo que se mantiene a mano es una
lista corta de **exenciones razonadas**. La diferencia importa: olvidarse de añadir a una lista de
exenciones falla del lado seguro, y olvidarse de añadir a una lista de vigilados no.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RAIZ = Path("app")
_DIRECTORIOS = (_RAIZ / "routers", _RAIZ / "api" / "v1")

# Señales de que un endpoint acota lo que devuelve. No es un análisis de flujo: es la presencia
# de la herramienta correcta en el fichero. Un router que no menciona ninguna de estas no puede
# estar acotando, y ésa es la afirmación que este test necesita.
_SENALES_DE_ACOTADO = (
    "tenancy",              # la capa: assert_org_access / scope_query_to_orgs
    "assert_chatbot_access",  # la puerta del chat y del widget
    "es_propietario",       # propiedad, en Informes
    "organizacion_ids",     # el claim, leído directamente del principal
)

# ─────────────────────────── Exenciones, con su razón ───────────────────────────

_SIN_ACOTAR = {
    "auth_router.py": "emite el token; antes de tenerlo no hay organizaciones que acotar",
    "saml_auth_router.py": "ACS y metadata del IdP: la credencial es la aserción firmada",
    "charts_router.py": "sin estado — dibuja con los datos que le manda el propio llamante",
    "pat_router.py": "acota por propiedad del token (owner_id); su ámbito lo resuelve PatService",
    # USR.9 — esta razón decía «los cuatro endpoints son de superadministrador. Cuando MT.9
    # los abra a un administrador harán falta scope_query_to_orgs y assert_org_access», y eso
    # ya pasó: el listado lo lee quien administra una organización, acotado con
    # `scope_query_to_orgs`, y fijar la contraseña usa `assert_org_access`. Sigue en la lista
    # porque crear, editar y borrar son de superadministrador y no acotan nada.
    "hub_users_router.py": (
        "listar y fijar contraseña YA acotan (scope_query_to_orgs, assert_org_access); crear, "
        "editar y borrar son de superadministrador y por eso no acotan"
    ),
    "hub_opciones_router.py": (
        "no sirve datos de ningún inquilino: sirve el contrato —qué modos de idioma existen y "
        "qué idiomas se ofrecen—, idéntico para todos. No hay nada que acotar, y el día que "
        "necesite una sesión de base de datos será porque dejó de ser contrato"
    ),
    "hub_modulos_router.py": (
        "de superadministrador. La dimensión de organización de las concesiones (MT.5) está "
        "en la tabla y todavía no la consume nadie: es MT.14"
    ),
    # `hub_agents_router.py` estuvo aquí hasta SEC.9.6, que le puso el filtro por el
    # `workspace_id` de la ruta y `assert_chatbot_org_access`. Ya no necesita exención.
    "edge_sync.py": (
        "dos stubs 501. **Cuando se implemente nace abierto si nadie mira**: GET /edge/config "
        "está diseñado para servir un snapshot de configuración cloud"
    ),
    # VAS.1 — cómputo puro: aplica el contrato de citas al texto que le manda el llamante y no
    # recibe sesión de base de datos, así que no hay nada que acotar.
    #
    # **Esta exención caduca en VAS.2**, que añade la consulta de vigencia y con ella la
    # acotación por tenencia sobre `hub_chatbots`. Cuando eso entre, la línea se va: dejarla
    # puesta convertiría una exención cierta en una que tapa lo que viniera después.
    "verificaciones_router.py": (
        "cómputo puro sobre el texto del llamante (contrato de citas); sin sesión de base de "
        "datos. Caduca en VAS.2, que trae la vigencia y su acotación por tenencia"
    ),
    # REG.3 — mismo caso que `charts_router`: no lee nada, así que no hay nada que acotar.
    "anonimizacion_router.py": (
        "sin estado — detecta y sustituye PII en el texto que le manda el propio llamante, y no "
        "guarda ni consulta nada (hay un test que cuenta todas las tablas operacionales antes y "
        "después). No recibe sesión de base de datos: el día que la necesite, esta exención deja "
        "de valer y hay que releerla"
    ),
}

# Routers que declaran su módulo en el docstring y **todavía no lo exigen** con `require_module`.
#
# Esta lista sólo puede ENCOGER. Está aquí y no borrada porque añadir la guarda a un router que
# hoy sirve al piloto puede dejar fuera a quien no tenga la concesión, y eso es una decisión de
# despliegue —PLAT/MT fase 2—, no un arreglo de seguridad de este bloque. Lo que sí arregla este
# test es que **el siguiente router que se escriba no pueda estrenar el desajuste**.
_DECLARAN_SIN_EXIGIR = {
    "hub_users_router.py",
    "hub_modulos_router.py",
    "hub_ingestion_router.py",
    "hub_prompt_templates_router.py",
    "hub_content_quality_router.py",
    "hub_sites_router.py",
    # Comprueba rol y pertenencia del chatbot en `_guarda_del_chatbot` (SEC.8.1), pero no el
    # módulo. Mismo riesgo de dejar fuera a un administrador que los otros de `chatbots`.
    "hub_test_scenarios_router.py",
}

# Ficheros con APIRouter que main.py no registra, y por qué no es superficie muerta.
_NO_REGISTRADOS: dict[str, str] = {}


def _routers() -> dict[str, Path]:
    """Todos los ficheros que definen un `APIRouter`, descubiertos recorriendo el árbol."""
    encontrados: dict[str, Path] = {}
    for directorio in _DIRECTORIOS:
        for ruta in sorted(directorio.rglob("*.py")):
            if ruta.name == "__init__.py":
                continue
            if "APIRouter(" in ruta.read_text(encoding="utf-8"):
                encontrados[ruta.name] = ruta
    return encontrados


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _modulo_declarado(texto: str) -> str | None:
    encaje = re.search(r"Módulo:\s*([a-z_]+)", texto)
    return encaje.group(1) if encaje else None


class TestElInventarioSeRecorre:

    def test_should_walk_registered_routers_not_a_fixed_list(self):
        """La red se teje recorriendo, no enumerando.

        El número exacto no importa y no se fija: lo que se fija es que el recorrido **encuentra
        routers**. Un `rglob` que deje de encontrarlos —porque cambió la estructura de
        directorios— dejaría todos los tests de este fichero en verde sin comprobar nada, que es
        el modo de fallo más peligroso de un guardarraíl.
        """
        encontrados = _routers()
        assert len(encontrados) >= 25, (
            f"el recorrido sólo encontró {len(encontrados)} routers: si la estructura de "
            "directorios cambió, este fichero está comprobando el vacío"
        )
        assert "hub_chatbots_router.py" in encontrados
        assert "hub_chat.py" in encontrados

    def test_should_not_leave_a_router_unregistered(self):
        """Un router con endpoints que `main.py` no registra es superficie muerta —o peor, viva
        y sin vigilar—. La auditoría de julio encontró 1.200 líneas así."""
        main = _texto(_RAIZ / "main.py")
        huerfanos = [
            nombre
            for nombre in _routers()
            if nombre[:-3] not in main and nombre not in _NO_REGISTRADOS
        ]
        assert huerfanos == [], (
            f"estos routers definen endpoints y main.py no los menciona: {huerfanos}. "
            "O se registran, o se retiran, o se declaran en _NO_REGISTRADOS con su razón."
        )


class TestNingunRouterNuevoSeSaltaLaTenencia:

    def test_should_fail_when_a_new_router_lacks_tenancy_and_is_not_exempted(self):
        faltan = []
        for nombre, ruta in _routers().items():
            if nombre in _SIN_ACOTAR:
                continue
            texto = _texto(ruta)
            if not any(senal in texto for senal in _SENALES_DE_ACOTADO):
                faltan.append(nombre)

        assert faltan == [], (
            "estos routers sirven datos y no mencionan ninguna forma de acotarlos "
            f"{_SENALES_DE_ACOTADO}: {faltan}.\n"
            "Si es correcto que no acoten, añádelos a _SIN_ACOTAR **con su razón**; si no, es "
            "el hallazgo A2 otra vez por un endpoint que nadie acordó revisar."
        )

    def test_should_keep_every_exemption_justified(self):
        """Una exención sin razón es un agujero con permiso. Y una que sobra es peor: tapa un
        router que sí habría que revisar."""
        sin_razon = [n for n, razon in _SIN_ACOTAR.items() if not razon.strip()]
        assert sin_razon == [], f"exenciones sin razón escrita: {sin_razon}"

        encontrados = set(_routers())
        sobran = sorted(set(_SIN_ACOTAR) - encontrados)
        assert sobran == [], (
            f"estas exenciones ya no corresponden a ningún router: {sobran}. Una lista de "
            "exenciones que no se poda acaba eximiendo a ficheros que no existen y tapando "
            "a los que sí."
        )


class TestElDocstringNoAutoriza:
    """El fallo de método que dejó pasar SEC.9.1, convertido en test.

    `test_plat5_frontera_de_modulos.py` comprueba que cada router **declare** su módulo en el
    docstring, que es lo que manda `AGENTS.md`. Eso sigue valiendo y no se retira. Lo que faltaba
    es la otra mitad: que lo declarado **se exija** con una dependencia real.
    """

    def test_should_require_real_dependencies_not_docstring(self):
        incumplen = []
        for nombre, ruta in _routers().items():
            texto = _texto(ruta)
            modulo = _modulo_declarado(texto)
            if modulo is None or nombre in _DECLARAN_SIN_EXIGIR:
                continue
            if f'require_module("{modulo}")' not in texto:
                incumplen.append(f"{nombre} (declara «{modulo}» y no lo exige)")

        assert incumplen == [], (
            "estos routers declaran un módulo en el docstring y no lo hacen cumplir con "
            f"require_module: {incumplen}. Un docstring no autoriza nada — es exactamente lo "
            "que dejó a library_router abierto pasando el check de PLAT.5 en verde."
        )

    def test_should_only_shrink_the_pending_list(self):
        """La lista de desajustes conocidos es un trinquete: se puede vaciar, no engordar."""
        assert len(_DECLARAN_SIN_EXIGIR) <= 7, (
            "_DECLARAN_SIN_EXIGIR ha crecido. Es una lista de deuda heredada de antes de "
            "SEC.9.5, no un sitio donde apuntar routers nuevos: el router nuevo se escribe "
            "con su guarda."
        )
        encontrados = set(_routers())
        sobran = sorted(_DECLARAN_SIN_EXIGIR - encontrados)
        assert sobran == [], f"entradas que ya no existen: {sobran}"


class TestLaListaViejaNoTieneNombresMuertos:
    """El guardarraíl de SEC.2 se saltaba en silencio los nombres que no encontraba."""

    def test_should_not_keep_a_name_that_matches_no_file(self):
        """Se lee el fichero en vez de importarlo: `tests/` no es un paquete, y de paso esto
        comprueba la lista tal y como está escrita, sin ejecutar nada de ese módulo."""
        fuente = Path("tests/api/test_tenant_isolation.py").read_text(encoding="utf-8")
        bloque = fuente.split("ROUTERS = (", 1)[1].split(")", 1)[0]
        nombres = re.findall(r'"([^"]+\.py)"', bloque)
        assert nombres, "no se pudo leer la lista ROUTERS del guardarraíl de SEC.2"

        inexistentes = [
            n
            for n in nombres
            if not any((base / n).is_file() for base in _DIRECTORIOS)
        ]
        assert inexistentes == [], (
            f"la lista de routers vigilados nombra ficheros que no existen: {inexistentes}. "
            "El `continue` los saltaba sin avisar, así que parecían cubiertos."
        )
