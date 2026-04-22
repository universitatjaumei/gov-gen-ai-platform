"""Tests de importación para client_app."""

def test_database_models_import():
    from app.database.models import RpaPlaybook, ExtractionLog
    assert RpaPlaybook is not None
    assert ExtractionLog is not None

def test_services_import():
    from app.services.sandbox_service import SandboxExecutionService
    assert SandboxExecutionService is not None

