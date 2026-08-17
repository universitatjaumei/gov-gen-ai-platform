"""VER.1 — la generación de informes se ejecuta de verdad.

`POST /redaccion/workspaces/{id}/run` prometía una ejecución y no la hacía: cambiaba el
estado a `drafting`, devolvía un `run_id` que no identificaba nada y ahí acababa. Lo decía el
propio código (`workspace_run_service.py`: «Para el MVP no dispara la ejecución del grafo en
background»). Para quien usa el panel eso es indistinguible de un informe que tarda, y
esperará indefinidamente.

El `DraftingCoreGraph` **ya estaba construido**, con sus 14 nodos y sus tests. Lo que faltaba
era la raíz de composición —quién le pasa el repositorio de versiones, el almacenamiento, la
factoría de extracción y el modelo— y **persistir lo que sale**: hasta hoy nadie escribía
nunca una fila en `hub_workspace_blocks`, así que un informe generado no existía en ningún
sitio al terminar la petición.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
)
from server.app.modules.redaccion.contracts.ui import ReportUIContract
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubRunManifest,
    HubWorkspace,
    HubWorkspaceBlock,
)

TEXTO_GENERADO = "Resumen ejecutivo del periodo, redactado por el modelo."


def _spec() -> ReportTemplateSpec:
    """Plantilla mínima con un bloque de IA: es el camino que la generación tiene que cubrir."""
    return ReportTemplateSpec(
        sections=[],
        blocks=[
            AIAssistedTextBlock(
                id="b_resumen",
                title="Resumen ejecutivo",
                ai_prompt_template_id="resumen_v1",
                review_policy_id="required",
            )
        ],
        input_contract=InputContract(),
        ui_contract=ReportUIContract(
            wizard_steps=[], dropzones=[], manual_fields=[],
            block_editor_enabled=False, ai_review_panel_enabled=True,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.ALLOWED,
        review_policy=ReviewPolicy.REQUIRED,
        export_policy=ExportPolicy.DOCX,
    )


def _llm(texto: str = TEXTO_GENERADO) -> MagicMock:
    servicio = MagicMock()
    servicio.model_name = "modelo-de-prueba"
    servicio.generate = AsyncMock(return_value=texto)
    return servicio


async def _sembrar(session, spec: ReportTemplateSpec | None = None) -> uuid.UUID:
    """Plantilla + versión + workspace listo para generar. Devuelve el workspace."""
    plantilla = HubReportTemplate(
        name=f"Plantilla {uuid.uuid4().hex[:6]}",
        report_profile="GENERIC_REPORT",
        owner_kind="platform",
        is_global=True,
    )
    session.add(plantilla)
    await session.flush()

    version = HubReportTemplateVersion(
        template_id=plantilla.id,
        version=1,
        spec_json=(spec or _spec()).model_dump(mode="json"),
        created_by=uuid.uuid4(),
    )
    session.add(version)
    await session.flush()
    plantilla.current_version_id = version.id

    workspace = HubWorkspace(
        template_version_id=version.id,
        owner_id=uuid.uuid4(),
        status="drafting",
    )
    session.add(workspace)
    await session.flush()
    return workspace.id


async def _corromper_la_spec(session, workspace_id: uuid.UUID) -> None:
    """Deja la versión de plantilla con una spec que ya no valida.

    Es el fallo realista del módulo: una plantilla guardada con un formato que el contrato
    actual ya no acepta. Apuntar el workspace a una versión inexistente no sirve —hay una FK
    que lo impide— y forzar el fallo desde el modelo tampoco: el nodo de IA captura los
    errores por bloque a propósito y el grafo termina bien.
    """
    workspace = await session.get(HubWorkspace, workspace_id)
    version = await session.get(HubReportTemplateVersion, workspace.template_version_id)
    version.spec_json = {"sections": "esto no es una lista de secciones"}


class TestLaGeneracionProduceAlgo:

    @pytest.mark.asyncio
    async def test_should_persist_the_blocks_it_generated(self, db_url):
        """Nadie escribía nunca en `hub_workspace_blocks`: el informe se generaba —cuando se
        generaba— y se perdía al terminar la petición."""
        from server.app.modules.redaccion.services.drafting_runner import ejecutar_borrador

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                await session.commit()

                await ejecutar_borrador(workspace_id, session, llm_service=_llm())

                filas = (await session.execute(
                    select(HubWorkspaceBlock).where(
                        HubWorkspaceBlock.workspace_id == workspace_id
                    )
                )).scalars().all()

                assert [f.block_id for f in filas] == ["b_resumen"]
                assert TEXTO_GENERADO in str(filas[0].content_json)
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_should_leave_the_workspace_waiting_for_review(self, db_url):
        """El grafo se detiene en la puerta de revisión: el estado tiene que decirlo, porque
        es lo que hace que la pantalla ofrezca aprobar o rechazar."""
        from server.app.modules.redaccion.services.drafting_runner import ejecutar_borrador

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                await session.commit()

                await ejecutar_borrador(workspace_id, session, llm_service=_llm())

                workspace = await session.get(HubWorkspace, workspace_id)
                await session.refresh(workspace)
                assert workspace.status == "in_review"
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_should_persist_a_run_manifest_pointed_at_by_the_workspace(self, db_url):
        """El manifiesto es la trazabilidad de la ejecución. Sin el puntero desde el
        workspace, existe pero no se puede encontrar."""
        from server.app.modules.redaccion.services.drafting_runner import ejecutar_borrador

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                await session.commit()

                await ejecutar_borrador(workspace_id, session, llm_service=_llm())

                workspace = await session.get(HubWorkspace, workspace_id)
                await session.refresh(workspace)
                manifiestos = (await session.execute(
                    select(HubRunManifest).where(
                        HubRunManifest.workspace_id == workspace_id
                    )
                )).scalars().all()

                assert len(manifiestos) == 1
                assert workspace.run_manifest_id == manifiestos[0].id
        finally:
            await engine.dispose()


class TestLosDatosDePartida:

    @pytest.mark.asyncio
    async def test_should_hand_the_uploaded_inputs_to_the_graph(self, db_url):
        """Visto en vivo en VER.4: se sube el Excel, se genera, y los bloques deterministas
        siguen en `draft` porque el ejecutor arrancaba el grafo con `inputs={}`. El informe
        salía sin datos y el bloque de IA decía, con razón, que no tenía con qué redactar."""
        from server.app.modules.redaccion.services import drafting_runner

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                workspace = await session.get(HubWorkspace, workspace_id)
                workspace.inputs_json = {
                    "datos_excel": {
                        "slot_id": "datos_excel",
                        "filename": "datos.xlsx",
                        "storage_path": "redaccion/x/inputs/datos_excel/datos.xlsx",
                        "size_bytes": 10,
                        "uploaded_at": "2026-08-17T00:00:00+00:00",
                    }
                }
                await session.commit()

                # Se relee tras el commit: `expire_on_commit` deja el objeto anterior con
                # los atributos expirados y leerlos dispara una recarga síncrona.
                workspace = await session.get(HubWorkspace, workspace_id)
                version = await session.get(
                    HubReportTemplateVersion, workspace.template_version_id
                )
                estado = drafting_runner._estado_inicial(
                    workspace, ReportTemplateSpec.model_validate(version.spec_json)
                )

                assert "datos_excel" in estado.inputs
                assert estado.inputs["datos_excel"].filename == "datos.xlsx"
        finally:
            await engine.dispose()


class TestReanudar:

    @pytest.mark.asyncio
    async def test_should_keep_what_a_human_already_approved(self, db_url):
        """Reanudar arrancaba el grafo de cero, así que continuar tras aprobar el texto de
        IA borraba esa aprobación y lo volvía a generar: lo contrario de lo que pide quien
        pulsa continuar."""
        from server.app.modules.redaccion.database.models import HubWorkspaceBlock
        from server.app.modules.redaccion.services import drafting_runner

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                session.add(HubWorkspaceBlock(
                    workspace_id=workspace_id,
                    block_id="b_resumen",
                    kind="AI_ASSISTED_TEXT",
                    status="approved",
                    content_json={"text": "Lo aprobó una persona."},
                ))
                await session.commit()

                workspace = await session.get(HubWorkspace, workspace_id)
                version = await session.get(
                    HubReportTemplateVersion, workspace.template_version_id
                )
                filas = (await session.execute(
                    select(HubWorkspaceBlock).where(
                        HubWorkspaceBlock.workspace_id == workspace_id
                    )
                )).scalars().all()

                estado = drafting_runner._estado_inicial(
                    workspace,
                    ReportTemplateSpec.model_validate(version.spec_json),
                    list(filas),
                )

                assert estado.blocks["b_resumen"].status == "approved"
                assert estado.blocks["b_resumen"].content == {"text": "Lo aprobó una persona."}
        finally:
            await engine.dispose()


class TestCuandoLaGeneracionFalla:

    @pytest.mark.asyncio
    async def test_should_leave_the_workspace_in_error_and_not_stuck_drafting(self, db_url):
        """Un workspace atascado en `drafting` para siempre es peor que uno que dice que
        falló: el primero se lee como «va lento» y nadie lo mira nunca."""
        from server.app.modules.redaccion.services.drafting_runner import ejecutar_borrador

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                await _corromper_la_spec(session, workspace_id)
                await session.commit()

                await ejecutar_borrador(workspace_id, session, llm_service=_llm())

                workspace = await session.get(HubWorkspace, workspace_id)
                await session.refresh(workspace)
                assert workspace.status == "error"
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_should_say_what_went_wrong(self, db_url):
        """«error» a secas obliga a mirar los logs del servidor. El motivo viaja con el
        workspace, que es donde lo busca quien usa el panel."""
        from server.app.modules.redaccion.services.drafting_runner import ejecutar_borrador

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:
                workspace_id = await _sembrar(session)
                await _corromper_la_spec(session, workspace_id)
                await session.commit()

                await ejecutar_borrador(workspace_id, session, llm_service=_llm())

                workspace = await session.get(HubWorkspace, workspace_id)
                await session.refresh(workspace)
                assert any(
                    "error" in str(aviso).lower() or "not found" in str(aviso).lower()
                    for aviso in (workspace.warnings_json or [])
                ), f"el workspace no dice por que fallo: {workspace.warnings_json}"
        finally:
            await engine.dispose()
