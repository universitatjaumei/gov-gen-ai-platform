"""Tests para verificar la separación de modelos en el límite edge-cloud."""

def test_config_base_contains_only_config_models() -> None:
    from server.app.modules.agents_hub.database.base import HubConfigBase
    import server.app.modules.agents_hub.database.config_models  # noqa: F401

    # Verify that metadata contains exactly the expected config tables
    tables = set(HubConfigBase.metadata.tables.keys())
    assert tables == {
        "hub_organizaciones",
        "hub_chatbots",
        "hub_llm_configs",
        "hub_prompt_templates",
        "hub_providers",
        # Personas y PAT (AUTH.2 / AUTH.3) — configuración cloud→edge. La tabla se
        # llama `hub_users` desde IDE.2: era de SSO cuando su único escritor era el ACS.
        "hub_users",
        "hub_personal_access_tokens",
        # Vocabulario controlado del corpus (ING.0.1) — ámbitos y submaterias son
        # configuración institucional, no dato operacional del cliente: se
        # sincronizan cloud→edge y los módulos edge los leen vía ConfigProvider.
        "hub_vocabulary_terms",
        # Temas de identidad visual (SEC.8.6) — colores, tipografía y logotipo de la
        # institución. Es configuración, del mismo lado que los prompts: no contiene
        # dato del cliente final y el edge la necesita para pintar el widget, así que
        # viaja cloud→edge. Vivían como ficheros locales, que en Cloud Run desaparecían
        # al reciclarse el contenedor.
        "hub_themes",
        # Credencial de sitio del widget (SEC.8.5) — sustituye al Bearer privilegiado que
        # el widget embebía en el HTML. Es configuración de publicación del chatbot, no
        # identidad ni dato del cliente final: no lleva rol ni organizaciones.
        "hub_widget_keys",
        # Override del prompt y del nivel de una actividad de plataforma (PRO.2.1) — del
        # mismo lado que `hub_prompt_templates`: es lo que se le dice a un modelo y con qué
        # nivel corre, no dato del cliente final. El edge lo lee vía ConfigProvider.
        "hub_activity_prompts",
        # Módulos de la plataforma y quién los tiene concedidos (INF.7) — es configuración
        # administrativa: se decide en el cloud y **el edge la necesita**, porque los routers
        # de informes, curación y automatización viven ahí y tienen que saber si quien pide un
        # informe puede pedirlo. No contiene dato del cliente final: el catálogo son cuatro
        # códigos y la concesión es un par (sujeto, módulo). Mismo lado que `hub_users`,
        # que también es identidad administrativa y no contenido.
        "hub_platform_modules",
        "hub_module_grants",
    }

def test_operational_base_contains_only_operational_models() -> None:
    from server.app.modules.agents_hub.database.base import HubOperationalBase
    import server.app.modules.agents_hub.database.operational_models  # noqa: F401
    import server.app.modules.redaccion.database.models  # noqa: F401 — tablas redaccion (edge)

    tables = set(HubOperationalBase.metadata.tables.keys())
    assert tables == {
        "hub_documents",
        "hub_document_chunks",
        "hub_interactions",
        "hub_ingestion_jobs",
        # Bloque 9Q (Calidad de contenido web) — entidades sitio/página/selección
        "hub_web_sites",
        "hub_crawled_pages",
        "hub_corpus_selections",
        # Módulo redacción (edge, 9R) — procesan expedientes del cliente
        "hub_report_templates",
        "hub_report_template_versions",
        "hub_workspaces",
        "hub_workspace_blocks",
        "hub_run_manifests",
        "hub_script_proposals",       # 9R.5.5 — scripts metaprogramados
        "hub_workspace_audit_events",  # 9R.5.x — auditoría de workspace
        # Bloque 9Q.1 — hallazgos de calidad de contenido
        "hub_content_findings",
        # RAG.13 — escenarios de prueba y su veredicto humano. Operacionales y no de
        # configuración: son las pruebas del cliente sobre su propio corpus, con sus
        # consultas reales dentro, así que no salen del edge.
        "hub_test_scenarios",
        "hub_test_runs",
        # SEC.4 — consumo por sujeto y ventana. Operacional y no configuración: el LÍMITE
        # se configura y viaja cloud→edge, pero lo GASTADO es dato del cliente final y no
        # sale del edge. Un contador colgado de `HubChatbot` se habría sincronizado con la
        # configuración, que es justo lo que la frontera existe para impedir.
        "hub_usage_counters",
    }

def test_no_cross_base_relationships() -> None:
    """Introspect mappers: no relationship in HubConfigBase points to HubOperationalBase classes and vice versa."""
    from sqlalchemy.orm import class_mapper
    from server.app.modules.agents_hub.database.config_models import HubChatbot

    mapper = class_mapper(HubChatbot)
    relationships = [rel.key for rel in mapper.relationships]
    assert "document_chunks" not in relationships
    assert "interactions" not in relationships

def test_edge_sync_config_endpoint_exists_returns_501() -> None:
    from server.app.api.v1.edge_sync import router
    route = next((r for r in router.routes if r.path == "/edge/config"), None)
    assert route is not None
    assert "GET" in route.methods

def test_edge_sync_telemetry_endpoint_exists_returns_501() -> None:
    from server.app.api.v1.edge_sync import router
    route = next((r for r in router.routes if r.path == "/edge/telemetry"), None)
    assert route is not None
    assert "POST" in route.methods
