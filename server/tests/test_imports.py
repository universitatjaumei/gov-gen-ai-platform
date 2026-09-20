"""Tests de importacion para server."""


def test_database_models_import():
    """Verifica que los modelos de base de datos se importan correctamente."""
    from server.app.database.models import AIConfig, TokenLog, ModelPricing
    assert AIConfig is not None
    assert TokenLog is not None
    assert ModelPricing is not None


def test_database_db_import():
    """Verifica que el motor de base de datos se importa correctamente.

    Hasta BD.2 comprobaba también `init_server_db`, el `create_all` del arranque. Se retiró: el
    esquema lo define Alembic y la aplicación no crea tablas.
    """
    from server.app.database.db import server_engine
    assert server_engine is not None


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


# `test_agent_service_import` estuvo aquí y se fue con su servicio en APER.19: `agent_service`
# era el único importador de `browser-use` y no tenía llamantes de producción —el hallazgo M7 de
# la auditoría del 2026-08-10—. Un test que sólo comprueba que un módulo muerto importa mantiene
# vivo el módulo, que es justo lo que hacía. Lo que queda es
# `tests/infra/test_aper19_el_agente_navegador_se_retiro.py`, que comprueba lo contrario.
