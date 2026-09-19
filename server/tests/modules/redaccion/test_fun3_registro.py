"""FUN.3 — registrar no es aprobar, y el cableado que lo hace cierto.

La segunda mitad de FUN.3. El fichero hermano (`test_fun3_referencia.py`) fija el contrato del
bloque y el resolutor; aquí está lo que ocurre **al registrar**, que es donde la Instrucció
02/2026 cambia el flujo: en el nivel 2 la aprobación humana previa está prohibida como condición
para compartir, así que el filtro es automático (declaración responsable + auditoría sin
hallazgos críticos + prueba en sandbox) y la persona entra después.

Y el test de cableado, que está aquí por la lección de DIN.4: una capacidad que el arranque no
conecta no existe. Allí costó descubrir que la auto-ingesta llevaba meses sin correr en
producción porque nadie comprobaba el cableado; aquí se comprueba.
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError


def _modulo_de_la_migracion():
    """La migración de datos, cargada por ruta.

    `migrations/` no es un paquete importable —Alembic lo carga por fichero—, así que un
    `import_module` no la encuentra. Se carga igual que hace Alembic: por su ruta.
    """
    import importlib.util
    from pathlib import Path

    ruta = (
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "versions"
        / "e5fa9688d218_fun_3_las_plantillas_referencian_la_.py"
    )
    spec = importlib.util.spec_from_file_location("fun3_migracion", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _contrato(finalidad: str = "Contar las filas del fichero de gastos"):
    from server.app.modules.redaccion.contracts.funciones import ContratoFuncion

    return ContratoFuncion(
        slots=[],
        parametros=[],
        finalidad=finalidad,
        categorias_datos=["sin_datos_personales"],
    )


class TestRegistrarNoEsAprobar:

    @pytest.mark.asyncio
    async def test_should_register_and_be_usable_with_no_human_approval(self, db_session):
        """**El test que hace cierta la Instrucció.** Declaración + auditoría sin CRITICAL +
        sandbox superado, y la versión queda usable: nadie aprueba nada."""
        from server.app.modules.redaccion.funciones_resolver import ResolvedorDeFuncion
        from server.app.modules.redaccion.funciones_service import registrar_version

        funcion, version = await registrar_version(
            db_session,
            nombre="Contar filas",
            organizacion_id=uuid.uuid4(),
            code="result = {'free_text': 'ok'}",
            contrato=_contrato(),
            declarada_por=uuid.uuid4(),
            audit_result={"approved": True, "risk_level": "SAFE", "findings": []},
        )

        assert version.estado == "registrada"
        assert version.revisada_por is None
        ejecutable = await ResolvedorDeFuncion(db_session).resolver(funcion.id, 1)
        assert ejecutable.code == "result = {'free_text': 'ok'}"

    @pytest.mark.asyncio
    async def test_should_keep_the_warning_findings_in_the_file(self, db_session):
        """Un `WARNING` no bloquea —eso sería aprobación previa por la puerta de atrás— pero
        consta, porque es lo que la revisión posterior tiene que poder leer."""
        from server.app.modules.redaccion.funciones_service import registrar_version

        _funcion, version = await registrar_version(
            db_session,
            nombre="Con aviso",
            organizacion_id=uuid.uuid4(),
            code="result = {}",
            contrato=_contrato(),
            declarada_por=uuid.uuid4(),
            audit_result={
                "approved": True,
                "risk_level": "WARNING",
                "findings": [{"code": "RUTA_ABSOLUTA", "severity": "warning"}],
            },
        )

        assert version.estado == "registrada"
        assert version.audit_result_json["findings"][0]["code"] == "RUTA_ABSOLUTA"

    def test_should_refuse_a_contract_without_the_declaration(self):
        """La declaración es parte del contrato, así que sin finalidad el contrato ni se
        construye: no hay forma de registrar una versión sin declararla."""
        with pytest.raises(ValidationError):
            _contrato(finalidad="")

    @pytest.mark.asyncio
    async def test_should_refuse_to_register_without_someone_declaring(self, db_session):
        from server.app.modules.redaccion.funciones_service import (
            FuncionIncoherente,
            registrar_version,
        )

        with pytest.raises(FuncionIncoherente) as fallo:
            await registrar_version(
                db_session,
                nombre="Sin declarante",
                organizacion_id=uuid.uuid4(),
                code="result = {}",
                contrato=_contrato(),
                declarada_por=None,  # type: ignore[arg-type]
            )

        assert "declara" in str(fallo.value).lower()

    @pytest.mark.asyncio
    async def test_should_record_who_wrote_it_without_branching_on_it(self, db_session):
        """El caso mayoritario de la Instrucció: un script que ya funcionaba en el equipo de la
        persona (nivel 1). Pasa por el mismo auditor y el mismo sandbox —ninguna rama «si lo
        escribió la IA»— y lo único que cambia es `autoria`, que la revisión posterior quiere
        ver."""
        from server.app.modules.redaccion.funciones_service import registrar_version

        _f1, de_persona = await registrar_version(
            db_session, nombre="De persona", organizacion_id=uuid.uuid4(),
            code="result = {}", contrato=_contrato(), declarada_por=uuid.uuid4(),
            autoria="persona",
        )
        _f2, de_ia = await registrar_version(
            db_session, nombre="De la IA", organizacion_id=uuid.uuid4(),
            code="result = {}", contrato=_contrato(), declarada_por=uuid.uuid4(),
        )

        assert de_persona.autoria == "persona"
        assert de_ia.autoria == "ia"
        # Y las dos quedan igual de usables: la autoría no es una puerta.
        assert de_persona.estado == de_ia.estado == "registrada"

    @pytest.mark.asyncio
    async def test_should_publish_v2_without_touching_v1(self, db_session):
        """Publicar una corrección es una versión nueva y **la anterior no se toca**: es lo que
        hace que una plantilla anclada a v1 siga ejecutando v1."""
        from server.app.modules.redaccion.funciones_resolver import ResolvedorDeFuncion
        from server.app.modules.redaccion.funciones_service import registrar_version

        organizacion, declarante = uuid.uuid4(), uuid.uuid4()
        funcion, v1 = await registrar_version(
            db_session, nombre="Con arreglo", organizacion_id=organizacion,
            code="result = {'free_text': 'con el error'}", contrato=_contrato(),
            declarada_por=declarante,
        )
        _funcion, v2 = await registrar_version(
            db_session, nombre="Con arreglo", organizacion_id=organizacion,
            code="result = {'free_text': 'arreglado'}", contrato=_contrato(),
            declarada_por=declarante, funcion_id=funcion.id,
        )

        assert (v1.version, v2.version) == (1, 2)
        resolutor = ResolvedorDeFuncion(db_session)
        assert "con el error" in (await resolutor.resolver(funcion.id, 1)).code
        assert "arreglado" in (await resolutor.resolver(funcion.id, 2)).code


class TestElCableadoDeProduccion:
    """La lección de DIN.4, aplicada antes de que muerda: una capacidad que el arranque no
    conecta no existe."""

    def test_should_pass_the_resolver_when_building_the_production_graph(self):
        import inspect

        from server.app.modules.redaccion.services import drafting_runner

        assert "resolvedor_de_funciones=ResolvedorDeFuncion(session)" in inspect.getsource(
            drafting_runner
        )

    @pytest.mark.asyncio
    async def test_should_say_it_out_loud_when_a_graph_has_no_resolver(self):
        """Y si alguien construye el grafo sin él, el bloque lo dice en vez de ejecutar nada."""
        from server.app.modules.redaccion.funciones_resolver import FuncionNoEjecutable
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            DeterministicExtractionNode,
        )

        nodo = DeterministicExtractionNode(factory=object())

        class _Ref:
            funcion_id = uuid.uuid4()
            version = 1

        with pytest.raises(FuncionNoEjecutable) as fallo:
            await nodo._resolver_funcion(_Ref())

        assert "sin resolutor" in str(fallo.value)


class TestLaMigracionDeLasPlantillasVivas:
    """La conversión de un bloque con código incrustado, comprobada sobre su propia lógica.

    La migración se aplicó de verdad contra la base de desarrollo —12 bloques, 4 funciones, y
    un viaje de ida y vuelta que dejó 0 bloques con código—, y lo que se fija aquí es el
    reconocimiento de bloques, que es de donde sale ese recuento.
    """

    def test_should_find_the_blocks_that_carry_embedded_code(self):
        modulo = _modulo_de_la_migracion()

        spec = {
            "blocks": [
                {"id": "a", "kind": "DETERMINISTIC_DATA", "options": {"code": "x = 1"}},
                {"id": "b", "kind": "DETERMINISTIC_DATA", "options": {}},
                {"id": "c", "kind": "STATIC_TEXT", "options": {"code": "no cuenta"}},
                {"id": "d", "kind": "DETERMINISTIC_DATA"},
            ]
        }

        encontrados = [b["id"] for b in modulo._bloques_con_codigo(spec)]

        assert encontrados == ["a"]

    def test_should_read_a_blocks_dictionary_from_an_old_template(self):
        """`blocks` llegó a guardarse como diccionario (la corrección de PRO.3): la migración
        tiene que reconocerlo, o se dejaría atrás justo las plantillas más viejas."""
        modulo = _modulo_de_la_migracion()

        spec = {
            "blocks": {
                "a": {"id": "a", "kind": "DETERMINISTIC_DATA", "options": {"code": "x = 1"}}
            }
        }

        assert [b["id"] for b in modulo._bloques_con_codigo(spec)] == ["a"]


class TestElCaminoViejoNoQuedaVivo:
    """La retirada, comprobada estructuralmente y no de memoria.

    La regla del proyecto es que una migración no está completa hasta que el código original
    queda retirado. Aquí el original es «el código incrustado en la plantilla», y lo que queda
    de él tiene que ser nada: el contrato lo rechaza (fichero hermano) y **nadie lo escribe**.

    Lo que sí sigue vivo, y está bien que siga, son las dos llamadas al sandbox que prueban una
    propuesta (`/test` y `/admin-retest`): ahí el código va directo al pipeline para probarlo,
    no a una plantilla. El prompt de FUN.3 lo dice: el flujo de propuesta se conserva como la
    prueba en sandbox del registro.
    """

    def test_should_never_write_the_code_into_a_template_block(self):
        import uuid as _uuid

        from server.app.routers.redaccion.scripts_router import _embed_script_block

        spec = _embed_script_block(
            {}, {"funcion_id": str(_uuid.uuid4()), "version": 3}, "b-script",
            test_data_kind="xlsx",
        )

        bloque = [b for b in spec["blocks"] if b["id"] == "b-script"][0]
        assert "code" not in bloque["options"]
        assert "approved" not in bloque["options"]
        assert bloque["funcion_ref"]["version"] == 3

    def test_should_keep_the_sandbox_trial_as_the_only_place_that_passes_code(self):
        """Y las dos que quedan son las de la prueba, con su `source_kind` a la vista."""
        import inspect

        from server.app.routers.redaccion import scripts_router

        fuente = inspect.getsource(scripts_router)
        # Las apariciones de `options={"code"` son exactamente las dos pruebas en sandbox, y
        # las dos construyen un `ExtractionInput` con `source_kind="admin_script"`.
        assert fuente.count('options={"code": proposal.code, "approved": True}') == 2
