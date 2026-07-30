"""Tests de importacion para server."""
import pytest


def test_database_models_import():
    """Verifica que los modelos de base de datos se importan correctamente."""
    from server.app.database.models import AIConfig, TokenLog, ModelPricing, ExtractionServiceConfig
    assert AIConfig is not None
    assert TokenLog is not None
    assert ModelPricing is not None
    assert ExtractionServiceConfig is not None


def test_database_db_import():
    """Verifica que el motor de base de datos se importa correctamente."""
    from server.app.database.db import server_engine, init_server_db
    assert server_engine is not None
    assert init_server_db is not None


def test_services_pricing_import():
    """Verifica que pricing_service se importa correctamente."""
    from server.app.services.pricing_service import calculate_cost, update_prices_from_openrouter
    assert calculate_cost is not None
    assert update_prices_from_openrouter is not None


def test_services_token_import():
    """Verifica que token_service se importa correctamente."""
    from server.app.services.token_service import log_token_usage, get_token_stats
    assert log_token_usage is not None
    assert get_token_stats is not None


def test_services_model_fetcher_import():
    """Verifica que model_fetcher se importa correctamente."""
    from server.app.services.model_fetcher import get_models_for_provider, refresh_model_cache
    assert get_models_for_provider is not None
    assert refresh_model_cache is not None


def test_services_api_key_import():
    """Verifica que api_key_service se importa correctamente."""
    from server.app.services.api_key_service import get_api_key
    assert get_api_key is not None


def test_agent_service_import():
    """Verifica que agent_service se importa correctamente."""
    from server.app.services.agent_service import BrowserAgentWrapper, AgentResult
    assert BrowserAgentWrapper is not None
    assert AgentResult is not None
