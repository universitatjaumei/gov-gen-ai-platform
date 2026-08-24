"""MT.1 — que el ámbito de una tabla sea una decisión y no un olvido.

La cascada «nulo = plataforma, se hereda» ya existe **dos veces** en el código —los temas
(`hub_themes`) y los valores por defecto de RAG (`HubOrganizacion.default_*`)— y cada una la
implementa a su manera. Antes de añadirla a cinco tablas más en MT.2…MT.6, se escribe una vez.

Y con ella un guardarraíl, que es la mitad que de verdad importa: **`hub_llm_configs` nació
global sin que nadie lo decidiera**, simplemente porque no había dónde decir lo contrario. La
auditoría del 2026-08-23 costó leer 31 tablas y 32 routers para descubrirlo. Una tabla de
configuración nueva que no declare su ámbito pone el test rojo, y entonces alguien decide.

**Este prompt no cambia comportamiento.** Declara lo que hay hoy, incluso donde lo que hay hoy
es lo que MT.2 y MT.6 van a cambiar: si aquí ya se declarase `HEREDABLE`, la declaración mentiría
sobre la base de datos y el diff de esos prompts no enseñaría la decisión.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from server.app.core.ambito import (
    Ambito,
    AmbitoNoDeclarado,
    ambito_de,
    de_esta_organizacion,
    resolver_cascada,
    tablas_sin_ambito,
)

UNA = uuid.uuid4()
OTRA = uuid.uuid4()

CAMPOS = ("color", "logotipo", "tipografia")


@dataclass
class _Fila:
    """Una fila cualquiera de una tabla heredable: lo único que exige el resolvedor es que
    tenga `organizacion_id` y los campos que se le pidan."""

    organizacion_id: uuid.UUID | None
    color: str | None = None
    logotipo: str | None = None
    tipografia: str | None = None


class TestLaCascadaSeResuelveUnaVez:

    def test_should_resolve_the_organisation_level_over_the_platform_one(self):
        filas = [
            _Fila(None, color="azul", logotipo="plataforma.png", tipografia="Inter"),
            _Fila(UNA, color="verde"),
        ]

        resuelto = resolver_cascada(filas, UNA, campos=CAMPOS)

        # Campo a campo: gana el de la organización donde lo pone, y lo que no pone lo sigue
        # mandando la plataforma. Un reemplazo de fila entera obligaría a cada organización a
        # repetir la configuración completa para cambiar un color.
        assert resuelto == {
            "color": "verde",
            "logotipo": "plataforma.png",
            "tipografia": "Inter",
        }

    def test_should_fall_back_to_the_platform_row(self):
        """Sin fila propia, la de plataforma entera. **Es lo que hace segura la fase 1**: con
        todas las filas de hoy a nulo, el piloto se comporta exactamente como ahora."""
        filas = [_Fila(None, color="azul", logotipo="plataforma.png")]

        resuelto = resolver_cascada(filas, UNA, campos=CAMPOS)

        assert resuelto["color"] == "azul"
        assert resuelto["logotipo"] == "plataforma.png"

    def test_should_not_merge_across_organisations(self):
        """**El test que importa.** Una resolución que ordene mal el `ORDER BY`, o que se
        quede con «la última fila que no sea de plataforma», devuelve la configuración del
        municipio de al lado sin que nada falle y sin que nadie lo note."""
        filas = [
            _Fila(None, color="azul"),
            _Fila(OTRA, color="rojo", logotipo="del-vecino.png"),
            _Fila(UNA, color="verde"),
        ]

        resuelto = resolver_cascada(filas, UNA, campos=CAMPOS)

        assert resuelto["color"] == "verde"
        assert resuelto["logotipo"] is None, "el logotipo del vecino no se hereda"

    def test_should_ignore_every_organisation_when_asked_for_the_platform(self):
        """Resolver «para la plataforma» no es resolver para nadie: es el nivel de arriba, y
        ninguna organización puede contaminarlo."""
        filas = [_Fila(None, color="azul"), _Fila(UNA, color="verde")]

        assert resolver_cascada(filas, None, campos=CAMPOS)["color"] == "azul"

    def test_should_treat_an_empty_string_as_a_value_and_none_as_inherit(self):
        """`None` es «heredar» y `""` es «lo quiero vacío». Colapsarlos haría imposible
        borrar un valor heredado desde la pantalla, que es justo lo que se pide de una
        cascada configurable."""
        filas = [_Fila(None, logotipo="plataforma.png"), _Fila(UNA, logotipo="")]

        assert resolver_cascada(filas, UNA, campos=CAMPOS)["logotipo"] == ""

    def test_should_survive_having_no_row_at_all(self):
        assert resolver_cascada([], UNA, campos=CAMPOS) == {
            "color": None,
            "logotipo": None,
            "tipografia": None,
        }

    def test_should_pick_the_row_of_one_organisation_only(self):
        """El filtro suelto, que es lo que consumirán los routers cuando quieran la fila y no
        los campos fundidos."""
        propia = _Fila(UNA, color="verde")
        filas = [_Fila(None), _Fila(OTRA), propia]

        assert de_esta_organizacion(filas, UNA) is propia
        assert de_esta_organizacion(filas, uuid.uuid4()) is None


class TestElAmbitoSeDeclara:

    def test_should_declare_the_scope_of_every_config_table(self):
        """Recorre los modelos de `HubConfigBase` y exige que cada uno diga de qué ámbito es.

        No es burocracia: la auditoría que originó este bloque consistió exactamente en
        reconstruir a mano esta lista, y `hub_llm_configs` era global porque nadie lo había
        decidido nunca.
        """
        sin_declarar = tablas_sin_ambito()

        assert sin_declarar == [], (
            "Estas tablas de configuración no declaran su ámbito. Añade "
            "`__ambito__` con el valor que corresponda: " + ", ".join(sin_declarar)
        )

    def test_should_catch_a_table_that_forgets_to_declare_it(self):
        """El criterio de cierre del prompt: el guardarraíl caza una tabla sintética."""

        class _TablaNueva:
            __tablename__ = "hub_algo_nuevo"

        with pytest.raises(AmbitoNoDeclarado):
            ambito_de(_TablaNueva)

    def test_should_require_a_path_when_the_scope_is_derived(self):
        """Una tabla que llega a la organización por otra tiene que decir **por dónde**.
        `DERIVADA` a secas no sirve de nada: quien lea el inventario de MT.7 seguiría sin
        saber si es por `chatbot_id` o por `site_id`."""

        class _SinCamino:
            __tablename__ = "hub_sin_camino"
            __ambito__ = Ambito.DERIVADA

        with pytest.raises(AmbitoNoDeclarado):
            ambito_de(_SinCamino)

    def test_should_not_let_a_table_inherit_the_scope_of_another(self):
        """Heredar de una base común es normal; heredar la decisión de quién es el dueño de los
        datos, no. Sin esto, una tabla nueva que extendiera a otra pasaría el guardarraíl con el
        ámbito del padre y nadie habría decidido nada — que es el olvido silencioso que este
        prompt existe para impedir."""

        class _Padre:
            __tablename__ = "hub_padre"
            __ambito__ = Ambito.PLATAFORMA

        class _Hija(_Padre):
            __tablename__ = "hub_hija"

        assert ambito_de(_Padre).ambito is Ambito.PLATAFORMA
        with pytest.raises(AmbitoNoDeclarado):
            ambito_de(_Hija)

    def test_should_say_which_column_leads_to_the_organisation(self):
        from server.app.modules.agents_hub.database.config_models import HubPromptTemplate

        declarado = ambito_de(HubPromptTemplate)

        assert declarado.ambito is Ambito.DERIVADA
        assert declarado.via == "chatbot_id"

    def test_should_declare_what_the_schema_sustains(self):
        """La etiqueta dice lo que la base de datos sostiene, no lo que se desea.

        Este test nació en MT.1 exigiendo `PLATAFORMA` en las dos, porque entonces las dos eran
        globales y declararlas heredables habría sido una etiqueta sin columna detrás. MT.2 le
        dio la columna a `hub_llm_configs`, así que ahora es heredable — y `hub_providers`
        **sigue siendo de plataforma**, esta vez por decisión y no por olvido: es un catálogo de
        tipos, y Google es Google en todos los municipios. Lo que se separó por organización es
        la credencial, en `HubProviderCredential`.
        """
        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
            HubProviderCredential,
        )

        assert ambito_de(HubLLMConfig).ambito is Ambito.HEREDABLE
        assert ambito_de(HubProvider).ambito is Ambito.PLATAFORMA
        assert ambito_de(HubProviderCredential).ambito is Ambito.HEREDABLE

    def test_should_not_claim_a_heredable_scope_without_the_column(self):
        """Coherencia entre la etiqueta y el esquema: `HEREDABLE` significa
        «`organizacion_id` nullable», y `ORGANIZACION` significa «NOT NULL». Una etiqueta que
        no case con la columna es peor que no tenerla, porque se lee como verdad.
        """
        import server.app.modules.agents_hub.database.config_models as modelos
        from server.app.modules.agents_hub.database.config_models import HubConfigBase

        incoherentes = []
        for cls in vars(modelos).values():
            if not (
                isinstance(cls, type)
                and issubclass(cls, HubConfigBase)
                and cls is not HubConfigBase
            ):
                continue
            declarado = ambito_de(cls)
            columna = cls.__table__.columns.get("organizacion_id")
            if declarado.ambito is Ambito.HEREDABLE and (
                columna is None or not columna.nullable
            ):
                incoherentes.append(f"{cls.__tablename__}: heredable sin columna nullable")
            if declarado.ambito is Ambito.ORGANIZACION and (
                columna is None or columna.nullable
            ):
                incoherentes.append(f"{cls.__tablename__}: de organización sin columna NOT NULL")

        assert incoherentes == [], incoherentes
