from typing import List, Dict, Any, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    UserExtractionConfig, RpaPlaybook, ScriptLibrary
)
from client_app.app.services.custom_script_service import custom_script_service
from pathlib import Path

class ResourceListingService:
    """
    Servicio centralizado para listar todos los recursos configurables y automatismos
    disponibles que pueden ser utilizados como activos en pasos de flujos de trabajo.
    Actúa como un catálogo unificado para la interfaz de usuario.
    """

    async def list_extraction_configs(self) -> List[Dict[str, Any]]:
        """
        Lista las configuraciones de extracción de datos (robots de IA) del usuario.

        Returns:
            Lista de diccionarios con ID, nombre y descripción de cada configuración.
        """
        async with AsyncSession(client_engine) as session:
            stmt = select(UserExtractionConfig)
            result = await session.exec(stmt)
            configs = result.all()
            
            return [
                {
                    'id': c.service_id,
                    'name': c.name,
                    'description': c.description or ''
                }
                for c in configs
            ]
    
    async def list_rpa_playbooks(self) -> List[Dict[str, Any]]:
        """
        Lista los playbooks de RPA (automatización web) disponibles en el sistema.

        Returns:
            Lista de diccionarios con ID, nombre y descripción de los playbooks.
        """
        async with AsyncSession(client_engine) as session:
            stmt = select(RpaPlaybook)
            result = await session.exec(stmt)
            playbooks = result.all()
            
            return [
                {'id': p.id, 'name': p.name, 'description': p.description or ''}
                for p in playbooks
            ]
    
    async def list_custom_scripts(self, status: str = "validated") -> List[Dict[str, Any]]:
        """
        Lista los scripts personalizados (genéricos) registrados por el usuario.

        Args:
            status: Estado del script a filtrar (por defecto 'validated').

        Returns:
            Lista de diccionarios con los scripts encontrados.
        """
        try:
             scripts = await custom_script_service.get_all_scripts(status=status)
             return [
                 {'script_id': s.id, 'name': s.name, 'description': s.description or ''}
                 for s in scripts
             ]
        except Exception as e:
            # Fallback si falla servicio
            print(f"Error listing scripts: {e}")
            return []
    
    async def list_etl_scripts(self) -> List[Dict[str, Any]]:
        """
        Lista los scripts específicos destinados a tareas de transformación ETL.

        Returns:
            Lista de diccionarios filtrados por la categoría 'etl'.
        """
        try:
            # Opción 1: Si hay campo 'category' en CustomScript
            scripts = await custom_script_service.get_all_scripts(status="validated")
            
            etl_scripts = [
                s for s in scripts 
                if hasattr(s, 'category') and s.category == 'etl'
            ]
            
            return [
                {'script_id': s.id, 'name': s.name, 'description': s.description or ''}
                for s in etl_scripts
            ]
        except Exception:
            return []
    
    async def list_report_templates(self) -> List[Dict[str, Any]]:
        """
        Escanea el sistema de archivos en busca de plantillas de informes PDF (HTML).

        Returns:
            Lista de diccionarios con nombre de archivo, nombre legible y ruta absoluta.
        """
        try:
            from client_app.app.modules.factory.report_factory import REPORT_TEMPLATES_DIR
            
            templates_path = Path(REPORT_TEMPLATES_DIR)
            
            if not templates_path.exists():
                return []
            
            templates = []
            for file in templates_path.glob('*.html'):
                templates.append({
                    'filename': file.name,
                    'name': file.stem.replace('_', ' ').title(),
                    'path': str(file)
                })
            
            return templates
        except ImportError:
            return []
    

    async def list_credentials(self, service_type: str) -> List[Dict[str, Any]]:
        """
        Lista credenciales por tipo de servicio.
        
        Args:
            service_type: "IMAP", "SMTP", "API", etc.
        
        Returns:
            Lista de diccionarios con id, name, service_type
        """
        try:
            from client_app.app.services.mail_watcher_service import mail_watcher_service
            
            # MailWatcherService ya implementa list_credentials
            creds = await mail_watcher_service.list_credentials(service_type=service_type)
            
            return creds  # Ya retorna [{'id': ..., 'name': ...}]
        except ImportError:
            return []
    
    async def list_api_endpoints(self) -> List[Dict[str, Any]]:
        """
        Lista endpoints/conexiones API pre-configuradas.

        NOTA: Placeholder hasta que exista modelo APIEndpointConfig.
        Futuro: Tabla con URLs, métodos, headers pre-configurados.
        """
        # Placeholder for now until APIEndpointConfig exists
        return []

    async def list_script_library_atoms(
        self,
        source_module: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista todos los átomos de la ScriptLibrary.

        Args:
            source_module: Filtrar por módulo ('etl', 'extraction', 'custom', 'graphics')
            status: Filtrar por estado ('draft', 'validated', 'published')

        Returns:
            Lista de diccionarios con metadata de cada átomo
        """
        async with AsyncSession(client_engine) as session:
            stmt = select(ScriptLibrary)

            if source_module:
                stmt = stmt.where(ScriptLibrary.source_module == source_module)
            if status:
                stmt = stmt.where(ScriptLibrary.status == status)

            result = await session.exec(stmt)
            scripts = result.all()

            return [
                {
                    'id': s.id,
                    'name': s.name,
                    'description': s.description or '',
                    'source_module': s.source_module,
                    'status': s.status or 'draft',
                    'tags': s.tags if hasattr(s, 'tags') else [],
                    'ui_contract': s.ui_contract if hasattr(s, 'ui_contract') else {},
                    'data_contract': s.data_contract if hasattr(s, 'data_contract') else {},
                    'created_at': s.created_at.isoformat() if s.created_at else None,
                    'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                    'is_favorite': s.is_favorite if hasattr(s, 'is_favorite') else False,
                    # Mapeo a StepType para consistencia con galería
                    'step_type': self._source_module_to_step_type(s.source_module)
                }
                for s in scripts
            ]

    def _source_module_to_step_type(self, source_module: str) -> str:
        """Mapea source_module a StepType para iconografía."""
        mapping = {
            'etl': 'ETL_TRANSFORM',
            'extraction': 'EXTRACTION',
            'custom': 'CUSTOM_SCRIPT',
            'graphics': 'REPORT_GENERATE',
            'pdf_tools': 'PDF_TOOLS',
        }
        return mapping.get(source_module, 'CUSTOM_SCRIPT')

# Singleton
resource_listing_service = ResourceListingService()
