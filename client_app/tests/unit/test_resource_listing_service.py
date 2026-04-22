import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.models import (
    UserExtractionConfig, RpaPlaybook
)
from client_app.app.services.resource_listing_service import ResourceListingService

# Mock external services
@pytest.fixture
def mock_external_services():
    with patch('client_app.app.services.resource_listing_service.custom_script_service') as script_svc: 
         # mail_watcher_service is imported locally
         
        # Setup default returns - use AsyncMock for awaitable methods
        script_svc.get_all_scripts = AsyncMock(return_value=[])
        
        yield script_svc

@pytest.mark.asyncio
async def test_list_extraction_configs(test_client_db):
    """Debe listar configuraciones de extracción"""
    
    with patch('client_app.app.services.resource_listing_service.client_engine', test_client_db):
        service = ResourceListingService()
        
        # 1. Sin datos
        result = await service.list_extraction_configs()
        assert result == []
        
        # 2. Insertar datos
        async with AsyncSession(test_client_db) as session:
            c1 = UserExtractionConfig(service_id="ext_001", name="Facturas", description="Desc 1")
            c2 = UserExtractionConfig(service_id="ext_002", name="Albaranes", description="Desc 2")
            session.add(c1)
            session.add(c2)
            await session.commit()
            
        # 3. Con datos
        result = await service.list_extraction_configs()
        assert len(result) == 2
        ids = [r['id'] for r in result]
        assert 'ext_001' in ids

@pytest.mark.asyncio
async def test_list_rpa_playbooks(test_client_db):
    """Debe listar playbooks RPA"""
    
    with patch('client_app.app.services.resource_listing_service.client_engine', test_client_db):
        service = ResourceListingService()
        
        async with AsyncSession(test_client_db) as session:
            p1 = RpaPlaybook(name="Login Web", base_url="http://test.com")
            session.add(p1)
            await session.commit()
            await session.refresh(p1)
            
        result = await service.list_rpa_playbooks()
        assert len(result) == 1
        assert result[0]['name'] == 'Login Web'

@pytest.mark.asyncio
async def test_list_custom_scripts(mock_external_services):
    """Debe listar scripts validados"""
    mock_script_svc = mock_external_services
    
    class MockScript:
        def __init__(self, id, name, desc):
            self.id = id
            self.name = name
            self.description = desc
            self.category = None
            
    mock_script_svc.get_all_scripts = AsyncMock(return_value=[
        MockScript(10, "Script A", "Desc A")
    ])
    
    service = ResourceListingService()
    result = await service.list_custom_scripts()
    
    assert len(result) == 1
    assert result[0]['script_id'] == 10
    
    mock_script_svc.get_all_scripts.assert_called_with(status="validated")

@pytest.mark.asyncio
async def test_list_etl_scripts(mock_external_services):
    """Debe listar scripts ETL filtrando por categoría"""
    mock_script_svc = mock_external_services
    
    class MockScript:
        def __init__(self, id, name, category):
            self.id = id
            self.name = name
            self.description = ""
            self.category = category
            
    mock_script_svc.get_all_scripts = AsyncMock(return_value=[
        MockScript(1, "ETL 1", "etl"),
        MockScript(2, "Other 1", "other"),
        MockScript(3, "ETL 2", "etl")
    ])
    
    service = ResourceListingService()
    result = await service.list_etl_scripts()
    
    assert len(result) == 2
    names = [r['name'] for r in result]
    assert "ETL 1" in names

@pytest.mark.asyncio
async def test_list_report_templates():
    """Debe listar templates HTML de reports"""
    service = ResourceListingService()
    
    # Mock report_factory module to avoid GTK/WeasyPrint import
    mock_rf_module = MagicMock()
    mock_rf_module.REPORT_TEMPLATES_DIR = "/mock/templates"
    
    # Also need to mock Path since service uses it on REPORT_TEMPLATES_DIR
    with patch.dict(sys.modules, {'client_app.app.modules.factory.report_factory': mock_rf_module}):
        with patch('client_app.app.services.resource_listing_service.Path') as MockPath:
            mock_path_instance = MockPath.return_value
            mock_path_instance.exists.return_value = True
            
            file1 = MagicMock()
            file1.name = "report1.html"
            file1.stem = "report1"
            file1.__str__.return_value = "/path/report1.html"
            
            mock_path_instance.glob.return_value = [file1]
            
            result = await service.list_report_templates()
            
            assert len(result) == 1
            assert result[0]['filename'] == "report1.html"

@pytest.mark.asyncio
async def test_list_credentials():
    """Debe delegar a mail_watcher_service"""
    service = ResourceListingService()
    
    # Patch the SOURCE module where mail_watcher_service is defined
    # But since that module (mail_watcher_service.py) does imports that might crash, we should mock the module itself
    mock_mws_module = MagicMock()
    mock_mws_instance = mock_mws_module.mail_watcher_service
    mock_mws_instance.list_credentials = AsyncMock(return_value=[{'id': 1, 'name': 'Cred 1'}])
    
    with patch.dict(sys.modules, {'client_app.app.services.mail_watcher_service': mock_mws_module}):
        result = await service.list_credentials("IMAP")
        
        assert len(result) == 1
        mock_mws_instance.list_credentials.assert_called_with(service_type="IMAP")

@pytest.mark.asyncio
async def test_list_api_endpoints(test_client_db):
    """Placeholder para API endpoints"""
    with patch('client_app.app.services.resource_listing_service.client_engine', test_client_db):
        service = ResourceListingService()
        result = await service.list_api_endpoints()
        assert result == []
@pytest.mark.asyncio
async def test_all_list_methods_exist():
    """Verificar que todos los métodos de listado existen"""
    service = ResourceListingService()
    
    methods = [
        'list_extraction_configs',
        'list_rpa_playbooks',
        'list_custom_scripts',
        'list_etl_scripts',
        'list_report_templates',
        'list_credentials',
        'list_api_endpoints'
    ]
    
    for method_name in methods:
        assert hasattr(service, method_name), f"Missing method: {method_name}"
        assert callable(getattr(service, method_name))
