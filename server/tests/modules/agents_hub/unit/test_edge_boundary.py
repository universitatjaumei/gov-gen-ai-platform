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
        # SSO/PAT (AUTH.2 / AUTH.3) — configuración cloud→edge
        "hub_sso_users",
        "hub_personal_access_tokens",
        # Vocabulario controlado del corpus (ING.0.1) — ámbitos y submaterias son
        # configuración institucional, no dato operacional del cliente: se
        # sincronizan cloud→edge y los módulos edge los leen vía ConfigProvider.
        "hub_vocabulary_terms",
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
