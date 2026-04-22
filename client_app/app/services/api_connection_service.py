from typing import List, Optional, Tuple, Dict, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from client_app.app.database.models import APIEndpointConfig
from client_app.app.modules.watchers.api_watcher import APIWatcher
import json
import logging

# Services
# Assuming we can reuse APIWatcher logic for testing single requests
# We might need to instantiate it temporarily

class APIConnectionService:
    async def list_configs(self) -> List[Dict[str, Any]]:
        """List all API configurations."""
        async with state.db_session() as session:
            stmt = select(APIEndpointConfig).order_by(APIEndpointConfig.name)
            results = await session.execute(stmt)
            configs = results.scalars().all()
            return [c.model_dump() for c in configs]

    async def get_config(self, config_id: int) -> Optional[APIEndpointConfig]:
        async with state.db_session() as session:
            return await session.get(APIEndpointConfig, config_id)

    async def save_config(self, config_data: Dict[str, Any]) -> int:
        """Create or update config."""
        async with state.db_session() as session:
            if config_data.get('id'):
                # Update
                config = await session.get(APIEndpointConfig, config_data['id'])
                if not config:
                    raise ValueError("Config not found")
                for k, v in config_data.items():
                    if k != 'id' and hasattr(config, k):
                        setattr(config, k, v)
                session.add(config)
                await session.commit()
                await session.refresh(config)
                return config.id
            else:
                # Create
                # Ensure JSON fields are strings if passed as dicts
                if isinstance(config_data.get('headers'), dict):
                    config_data['headers'] = json.dumps(config_data['headers'])
                if isinstance(config_data.get('body'), dict):
                    config_data['body'] = json.dumps(config_data['body'])
                if isinstance(config_data.get('pagination_config'), dict):
                    config_data['pagination_config'] = json.dumps(config_data['pagination_config'])
                
                config = APIEndpointConfig(**config_data)
                session.add(config)
                await session.commit()
                await session.refresh(config)
                return config.id

    async def delete_config(self, config_id: int) -> bool:
        async with state.db_session() as session:
            config = await session.get(APIEndpointConfig, config_id)
            if config:
                await session.delete(config)
                await session.commit()
                return True
            return False

    async def test_connection(self, config_id: int) -> Tuple[bool, str, Any]:
        """
        Test the connection.
        Returns: (success, message, response_data)
        """
        # We can reuse APIWatcher._fetch_with_pagination logic or just _fetch_page
        # But APIWatcher requires base_dir. We can mock or use temp dir.
        
        try:
            async with state.db_session() as session:
                config_model = await session.get(APIEndpointConfig, config_id)
                if not config_model:
                    return False, "Configuración no encontrada", None
                
                # Convert model to dict for watcher
                config = config_model.model_dump()
                # Parse JSON fields
                if isinstance(config.get('headers'), str):
                    config['headers'] = json.loads(config['headers'])
                
                # Prepare watcher config format
                auth_data = None
                if config_model.auth_credential_id:
                    from client_app.app.services.mail_watcher_service import mail_watcher_service
                    auth_data = await mail_watcher_service.get_credential(config_model.auth_credential_id)
                    # The APIWatcher expects a 'type' key in the auth dictionary
                    if auth_data and "type" not in auth_data:
                        auth_data["type"] = config_model.auth_type
                
                watcher_config = {
                    "url": config['url'],
                    "method": config['method'],
                    "auth": auth_data,
                    "headers": config['headers']
                }
                
                # If auth is linked, we need to fetch it (Not implemented fully in model yet, placeholder)
                # For now assume headers has auth or none
                
                from pathlib import Path
                import tempfile
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    watcher = APIWatcher(base_dir=Path(tmpdir))
                    
                    # We access the private method _fetch_with_pagination or _fetch_page
                    # Better to expose a public test method on watcher, but for now:
                    import httpx
                    headers = watcher._build_headers(watcher_config.get('auth'))
                    # Merge manual headers
                    if watcher_config.get('headers'):
                        try:
                            headers_data = json.loads(watcher_config['headers']) if isinstance(watcher_config['headers'], str) else watcher_config['headers']
                            headers.update(headers_data)
                        except:
                            pass
                        
                    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                        json_body = None
                        if config.get('body'):
                             try:
                                 json_body = json.loads(config['body'])
                             except:
                                 json_body = {}

                        response_data = await watcher._fetch_page(
                            client, 
                            watcher_config['url'], 
                            watcher_config['method'], 
                            headers,
                            json_body=json_body,
                            is_test=True
                        )
                        
                    return True, "Conexión exitosa", response_data

        except Exception as e:
            # Extraer el error real de tenacity si existe
            import tenacity
            if isinstance(e, tenacity.RetryError):
                actual_error = e.last_attempt.exception()
                msg = f"Error tras reintentos: {actual_error}"
            else:
                msg = str(e)

            # Logging seguro para Windows
            try:
                logging.error(f"API Test Failed: {msg}")
            except UnicodeEncodeError:
                logging.error(f"API Test Failed: {msg.encode('ascii', 'replace').decode()}")
            
            return False, msg, None

api_connection_service = APIConnectionService()
