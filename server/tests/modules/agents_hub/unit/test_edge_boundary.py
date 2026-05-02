"""Tests para verificar la separación de modelos en el límite edge-cloud."""

def test_config_base_contains_only_config_models() -> None:
    from server.app.modules.agents_hub.database.base import HubConfigBase
    import server.app.modules.agents_hub.database.config_models  # noqa: F401

    # Verify that metadata has exactly the 4 expected tables
    tables = set(HubConfigBase.metadata.tables.keys())
    assert tables == {
        "hub_clients",
        "hub_chatbots",
        "hub_llm_configs",
        "hub_prompt_templates",
        "hub_providers",
    }

def test_operational_base_contains_only_operational_models() -> None:
    from server.app.modules.agents_hub.database.base import HubOperationalBase
    import server.app.modules.agents_hub.database.operational_models  # noqa: F401

    tables = set(HubOperationalBase.metadata.tables.keys())
    assert tables == {
        "hub_documents",
        "hub_document_chunks",
        "hub_interactions",
        "hub_ingestion_jobs",
        "hub_ingestion_sources",
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
