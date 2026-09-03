"""REG.1 — el evento de actividad IA: contrato y tabla.

**Qué registra y qué no.** Esto es **registro de gobernanza**: quién usó qué agente, con qué
finalidad y sobre qué categorías de datos, al servicio de la conservación de registros del AI Act
y del registro de actividades de tratamiento del RGPD. **No** es trazado técnico: el detalle token
a token ya lo cubre la observabilidad interna de la plataforma y no se reconstruye aquí.

Registra actividad que ocurre **fuera** de la plataforma —agentes de terceros, asistentes de
código, herramientas de escritorio— para que una organización pueda responder «qué IA se usó
aquí» sin depender de que cada herramienta lo cuente a su manera.

**La regla dura del bloque: metadatos sí, payloads no.** El contrato no tiene ningún campo de
contenido y rechaza los no declarados. Si un caso exige evidencia del contenido, se guarda su
hash, nunca el contenido. El registro no puede convertirse en un segundo sitio donde vivan los
datos personales, porque entonces sería el problema que viene a resolver.

---

**Dos desviaciones documentadas respecto al prompt del plan**, ambas por lo que dice el código:

1. **El modelo NO declara `__ambito__`.** El prompt pedía `__ambito__ = "organizacion"` afirmando
   que «el guardarraíl de MT.1 lo exige igualmente», y eso es falso: MT.1 recorre **solo**
   `HubConfigBase`, y ningún modelo operacional declara ámbito. Declararlo aquí sería el único de
   trece, y nadie lo leería.
2. **`organizacion_id` va sin `ForeignKey`.** El prompt pedía FK «con el mismo patrón que las
   tablas operacionales vecinas», pero ese patrón es precisamente **no tener FK**: hay cero FK a
   `hub_organizaciones` en los modelos operacionales, a propósito, para que las dos bases
   declarativas sigan siendo separables cuando el despliegue parte cloud y edge.

Las dos se sustituyen por tests que fijan la regla correcta, porque el objetivo del prompt —que la
pertenencia a una organización sea explícita y esté vigilada— se cumple igual: la acotación la
garantizan el código y su test, no una restricción de la base de datos.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

ORG = uuid.UUID("735a5f55-7020-4c88-a374-c2b641c5b00b")


def _evento(**cambios):
    """Un evento válido mínimo, con los campos que el contrato exige."""
    base = {
        "ocurrido_en": datetime(2026, 9, 3, 10, 30, tzinfo=timezone.utc),
        "actor": "u-7f3a1c",
        "herramienta": "claude-cowork",
        "agente": "revisor-de-contratos",
        "finalidad": "Revisión previa de un pliego de licitación",
        "modelo_usado": "claude-opus-5",
        "categorias_datos": ["datos_identificativos", "datos_economicos"],
    }
    base.update(cambios)
    return base


# ──────────────────────── El contrato: metadatos sí, payloads no ───────────

class TestElContratoNoAdmiteContenido:
    """La regla dura del bloque, en el sitio donde se puede hacer cumplir."""

    @pytest.mark.parametrize("campo", ["payload", "content", "prompt", "mensaje", "texto"])
    def test_should_reject_any_undeclared_field(self, campo: str):
        """`extra="forbid"` y no ignorar: un campo aceptado en silencio haría creer que se guardó.

        Se prueban los cinco nombres con los que un integrador intentaría colar el contenido. No
        es paranoia: el contrato es la única barrera entre «registro de gobernanza» y «segunda
        copia de los datos personales».
        """
        from pydantic import ValidationError

        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        with pytest.raises(ValidationError):
            ActividadIAEvent(**_evento(**{campo: "cualquier cosa"}))

    def test_should_not_declare_any_content_field_at_all(self):
        """Ni ahora ni cuando alguien añada un campo: ningún nombre de contenido en el contrato.

        El test mira los campos declarados en vez de probar entradas, porque lo que hay que
        impedir es que el campo **exista**, no que se rechace su valor.
        """
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        prohibidos = {"payload", "content", "contenido", "prompt", "mensaje", "texto",
                      "respuesta", "completion", "input", "output"}
        declarados = set(ActividadIAEvent.model_fields)

        assert not (declarados & prohibidos), (
            f"el contrato del evento declara campos de contenido: {sorted(declarados & prohibidos)}. "
            "La regla del bloque es «metadatos sí, payloads no»: si hace falta evidencia del "
            "contenido, va su hash."
        )

    def test_should_accept_a_hash_as_the_only_evidence_of_content(self):
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        sin_hash = ActividadIAEvent(**_evento())
        assert sin_hash.payload_hash is None, "el hash es opcional: no todo uso lo aporta"

        h = "a" * 64
        con_hash = ActividadIAEvent(**_evento(payload_hash=h))
        assert con_hash.payload_hash == h

    @pytest.mark.parametrize("malo", ["abc", "a" * 63, "a" * 65, "z" * 64, "A" * 64])
    def test_should_refuse_something_that_is_not_a_sha256(self, malo: str):
        """Longitud y alfabeto. Un hash mal formado es un hash que no sirve para cotejar nada."""
        from pydantic import ValidationError

        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        with pytest.raises(ValidationError):
            ActividadIAEvent(**_evento(payload_hash=malo))


class TestLaFechaLlegaConZonaHoraria:
    """La lección de ACT.1: aware contra naive, y el cliente es quien declara la fecha."""

    def test_should_reject_a_naive_datetime(self):
        from pydantic import ValidationError

        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        with pytest.raises(ValidationError):
            ActividadIAEvent(**_evento(ocurrido_en=datetime(2026, 9, 3, 10, 30)))

    def test_should_accept_a_timezone_other_than_utc(self):
        """Quien registra puede estar en otro huso: se admite y se normaliza al comparar."""
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        madrid = timezone(timedelta(hours=2))
        evento = ActividadIAEvent(
            **_evento(ocurrido_en=datetime(2026, 9, 3, 12, 30, tzinfo=madrid))
        )

        assert evento.ocurrido_en.utcoffset() is not None


class TestLasCategoriasSonVocabulario:
    """Misma regla que el vocabulario del corpus: dato revisable, no estructura."""

    def test_should_accept_a_category_the_code_has_never_seen(self):
        """Sin `Enum`. Una categoría nueva no puede exigir una migración ni un despliegue.

        Es la regla del proyecto para todo vocabulario: si fuera `Enum` de Python o
        `CheckConstraint`, cada organización que necesitara una categoría propia tendría que
        esperar a una versión del núcleo.
        """
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        evento = ActividadIAEvent(
            **_evento(categorias_datos=["categoria_que_nadie_ha_declarado"])
        )

        assert evento.categorias_datos == ["categoria_que_nadie_ha_declarado"]

    def test_should_accept_an_empty_list_of_categories(self):
        """No todo uso trata datos personales, y decir «ninguna» es información."""
        from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent

        assert ActividadIAEvent(**_evento(categorias_datos=[])).categorias_datos == []


# ──────────────────────── El modelo: operacional, y sin ámbito ─────────────

class TestElModeloEsOperacional:
    """Las dos desviaciones del prompt, convertidas en las reglas que sí valen.

    Ver el docstring del módulo: el prompt pedía `__ambito__` y una FK, y ninguna de las dos
    corresponde a un modelo operacional de este proyecto.
    """

    def test_should_live_in_the_operational_base(self):
        from server.app.modules.agents_hub.database.base import HubOperationalBase
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        assert issubclass(HubActividadIA, HubOperationalBase), (
            "el registro es dato del cliente final: vive en la base operacional, que no se "
            "sincroniza al cloud."
        )
        assert HubActividadIA.__tablename__ == "hub_actividad_ia"

    def test_should_not_declare_ambito(self):
        """`__ambito__` es de `HubConfigBase`, que es lo único que MT.1 recorre.

        Declararlo en un modelo operacional lo convertiría en el único de trece que lo hace, sin
        que ningún guardarraíl lo lea: una declaración decorativa que la siguiente persona
        copiaría por analogía.
        """
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        assert "__ambito__" not in vars(HubActividadIA), (
            "un modelo operacional no declara ámbito. La acotación por organización la "
            "garantizan el código y su test, no una declaración que nadie comprueba."
        )

    def test_should_reference_the_organisation_without_a_foreign_key(self):
        """Sin FK, para que las dos bases declarativas sigan siendo separables.

        Es el patrón de todos los modelos operacionales: cero FK a `hub_organizaciones`. Con FK,
        un despliegue que parta cloud y edge no podría crear el esquema operacional sin arrastrar
        las tablas de configuración.
        """
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        columna = HubActividadIA.__table__.c.organizacion_id
        assert not columna.foreign_keys, (
            "`organizacion_id` no lleva FK en las tablas operacionales: es lo que mantiene "
            "separables la base de configuración y la operacional."
        )
        assert not columna.nullable, "el registro siempre pertenece a una organización"
        assert columna.index, "se consulta siempre acotado por organización"

    @pytest.mark.parametrize("columna", ["ocurrido_en", "herramienta"])
    def test_should_index_what_the_queries_filter_by(self, columna: str):
        """REG.5 filtra por herramienta y por rango de fechas."""
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        assert HubActividadIA.__table__.c[columna].index, (
            f"`{columna}` se usa como filtro en la lectura del registro y necesita índice."
        )


class TestLaTablaGuardaYDevuelve:

    async def test_should_round_trip_the_event_with_its_categories(self, db_session):
        """El viaje completo: las categorías van a JSONB y vuelven como lista."""
        from sqlalchemy import select

        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        fila = HubActividadIA(
            organizacion_id=ORG,
            **_evento(),
        )
        db_session.add(fila)
        await db_session.flush()

        recuperada = (
            await db_session.execute(
                select(HubActividadIA).where(HubActividadIA.id == fila.id)
            )
        ).scalar_one()

        assert recuperada.categorias_datos == ["datos_identificativos", "datos_economicos"]
        assert recuperada.herramienta == "claude-cowork"
        assert recuperada.organizacion_id == ORG

    async def test_should_stamp_when_it_was_recorded_by_itself(self, db_session):
        """`registrado_en` lo pone la base, no el cliente.

        Es la diferencia que importa para un registro de gobernanza: `ocurrido_en` lo declara
        quien registra —y puede mentir—, mientras que `registrado_en` es cuándo lo recibimos, y
        eso no lo elige nadie de fuera.
        """
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        fila = HubActividadIA(organizacion_id=ORG, **_evento())
        db_session.add(fila)
        await db_session.flush()
        await db_session.refresh(fila)

        assert fila.registrado_en is not None
        assert fila.registrado_en.tzinfo is not None, "timestamptz, no naive"

    async def test_should_keep_events_of_two_organisations_apart(self, db_session):
        """Dos organizaciones, dos filas, y cada una con la suya."""
        from sqlalchemy import select

        from server.app.modules.agents_hub.database.operational_models import HubActividadIA

        otra = uuid.uuid4()
        db_session.add(HubActividadIA(organizacion_id=ORG, **_evento()))
        db_session.add(
            HubActividadIA(organizacion_id=otra, **_evento(herramienta="copilot"))
        )
        await db_session.flush()

        de_la_otra = (
            await db_session.execute(
                select(HubActividadIA).where(HubActividadIA.organizacion_id == otra)
            )
        ).scalars().all()

        assert [f.herramienta for f in de_la_otra] == ["copilot"]
