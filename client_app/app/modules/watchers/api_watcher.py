# client_app/app/modules/watchers/api_watcher.py
import httpx
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
import logging

class APIWatcher:
    """
    Consumidor de APIs REST con soporte para:
    - Paginación (offset, cursor, next_url)
    - Autenticación (Bearer, Basic, API Key)
    - Reintentos con backoff exponencial
    - Guardado de respuestas en JSON/CSV

    Puede usarse tanto en modo batch (fetch_data) como polling (start_polling).
    """

    def __init__(
        self,
        base_dir: Path,
        workflow_engine=None,
        flow_id: Optional[str] = None
    ):
        """
        Args:
            base_dir: Directorio base para guardar responses
            workflow_engine: WorkflowEngine para trigger automático
            flow_id: ID del workflow a ejecutar tras fetch
        """
        self.base_dir = Path(base_dir)
        self.workflow_engine = workflow_engine
        self.flow_id = flow_id

        # Crear input dir
        self.input_dir = self.base_dir / "input"
        self.input_dir.mkdir(parents=True, exist_ok=True)

    def _safe_log(self, message: str, level: str = "error"):
        """Log level safe for Windows console/handlers with non-ASCII chars."""
        try:
            if level == "error":
                logging.error(message)
            else:
                logging.info(message)
        except UnicodeEncodeError:
            safe_msg = message.encode('ascii', 'replace').decode()
            if level == "error":
                logging.error(safe_msg)
            else:
                logging.info(safe_msg)

    def _build_headers(self, auth_config: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        Construye headers HTTP con autenticación.

        Soporta:
        - bearer: {"type": "bearer", "token": "..."}
        - basic: {"type": "basic", "user": "...", "password": "..."}
        - api_key: {"type": "api_key", "key": "...", "header": "X-API-Key"}
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        if not auth_config:
            return headers

        auth_type = auth_config.get("type")

        if auth_type == "bearer":
            token = auth_config.get("token")
            headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "basic":
            import base64
            user = auth_config.get("user")
            password = auth_config.get("password")
            credentials = f"{user}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif auth_type == "api_key":
            key = auth_config.get("key")
            header_name = auth_config.get("header", "X-API-Key")
            headers[header_name] = key

        return headers

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        method: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        is_test: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch de una página con lógica para decidir si reintentar (modo batch) 
        o fallar rápido (modo test/diseño).
        """
        if is_test:
            # En modo test usamos un timeout más corto (opcional) y sin reintentos
            return await self._execute_request(client, url, method, headers, params, json_body, timeout=20.0)
            
        return await self._fetch_page_with_retry(client, url, method, headers, params, json_body)

    @retry(
        retry=retry_if_not_exception_type(UnicodeEncodeError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _fetch_page_with_retry(self, *args, **kwargs):
        """Wrapper con reintentos para _execute_request."""
        return await self._execute_request(*args, **kwargs)

    async def _execute_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        method: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Core logic for HTTP requests with robust encoding and fallbacks."""
        try:
            # Handle non-ASCII URLs (IDNA + Quote)
            import urllib.parse
            if any(ord(c) > 127 for c in url):
                parsed = urllib.parse.urlsplit(url)
                netloc = parsed.netloc.encode('idna').decode('ascii')
                path = urllib.parse.quote(parsed.path)
                query = urllib.parse.quote(parsed.query, safe='=&')
                url = urllib.parse.urlunsplit(parsed._replace(netloc=netloc, path=path, query=query))

            # Defensive header sanitization (Wire safe ASCII)
            wire_headers = {}
            for k, v in headers.items():
                wire_headers[str(k).encode('ascii', 'ignore').decode()] = \
                    str(v).encode('ascii', 'xmlcharrefreplace').decode()

            # Prepare content for urllib fallback
            content = None
            if json_body:
                content = json.dumps(json_body).encode('utf-8')
                wire_headers["Content-Type"] = "application/json"

            # Generic request method
            try:
                if method.upper() in ["GET", "OPTIONS", "HEAD"]:
                    # GET usually doesn't have body, but httpx allows content
                    response = await client.request(
                        method=method.upper(), 
                        url=url, 
                        headers=wire_headers, 
                        params=params, 
                        timeout=timeout,
                        follow_redirects=True
                    )
                else:
                     response = await client.request(
                        method=method.upper(), 
                        url=url, 
                        headers=wire_headers, 
                        content=content,
                        timeout=timeout,
                        follow_redirects=True
                    )
                response.raise_for_status()
                return response.json()
                
            except Exception as httpx_error:
                # Fallback to urllib for stubborn Windows environments
                self._safe_log(f"[APIWatcher] HTTPX failed, trying urllib fallback: {httpx_error}", level="info")
                
                import urllib.request
                import urllib.error
                import asyncio
                
                # Re-construct full URL with params for GET
                full_url = url
                if params and method.upper() in ["GET", "OPTIONS", "HEAD"]: # Only add params to URL for GET-like requests
                    query_string = urllib.parse.urlencode(params)
                    full_url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"

                req = urllib.request.Request(full_url, method=method.upper())
                
                # Add headers
                for k, v in wire_headers.items():
                    req.add_header(k, v)
                
                # Add body
                if content and method.upper() not in ["GET", "OPTIONS", "HEAD"]: # Only add body for POST-like requests
                    req.data = content

                # Execute synchronous request in thread executor
                loop = asyncio.get_event_loop()
                
                def _urllib_request():
                    with urllib.request.urlopen(req, timeout=timeout) as f:
                        resp_body = f.read().decode('utf-8')
                        return json.loads(resp_body)

                return await loop.run_in_executor(None, _urllib_request)
        except UnicodeEncodeError as e:
            self._safe_log(f"[APIWatcher] Error de codificación en {method} {url}: {e}")
            raise
        except Exception as e:
            self._safe_log(f"[APIWatcher] Error en petición {method} {url}: {e}")
            raise

    async def _fetch_with_pagination(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fetch con soporte de paginación automática.

        Estrategias:
        - offset: ?offset=0&limit=100
        - cursor: ?cursor=abc123
        - next_url: sigue campo "next" en response
        """
        url = config["url"]
        method = config.get("method", "GET")
        auth = config.get("auth")
        pagination = config.get("pagination")
        max_pages = config.get("max_pages", 10)  # Límite de seguridad

        headers = self._build_headers(auth)
        
        # Extract and parse body if present
        json_body = None
        if config.get("body"):
            try:
                if isinstance(config["body"], str):
                    json_body = json.loads(config["body"])
                else:
                    json_body = config["body"]
            except:
                json_body = {}

        all_items = []
        page_count = 0

        async with httpx.AsyncClient() as client:
            if not pagination:
                # Sin paginación, fetch simple
                data = await self._fetch_page(client, url, method, headers, json_body=json_body)
                return data

            # Con paginación (Solo GET suele usar paginación, pero permitimos params/body por si acaso)
            pag_type = pagination.get("type")

            if pag_type == "offset":
                limit = pagination.get("limit", 100)
                offset = 0
                offset_param = pagination.get("offset_param", "offset")
                total_key = pagination.get("total_key", "total")
                items_key = pagination.get("items_key", "items")

                while page_count < max_pages:
                    params = {offset_param: offset, "limit": limit}
                    data = await self._fetch_page(client, url, method, headers, params=params, json_body=json_body)

                    items = data.get(items_key, [])
                    all_items.extend(items)

                    total = data.get(total_key, len(all_items))

                    offset += limit
                    page_count += 1

                    if len(all_items) >= total:
                        break

                return {items_key: all_items, total_key: len(all_items)}

            elif pag_type == "cursor":
                cursor_param = pagination.get("cursor_param", "cursor")
                cursor_key = pagination.get("cursor_key", "next_cursor")
                items_key = pagination.get("items_key", "items")

                cursor = None

                while page_count < max_pages:
                    params = {cursor_param: cursor} if cursor else {}
                    data = await self._fetch_page(client, url, method, headers, params=params, json_body=json_body)

                    items = data.get(items_key, [])
                    all_items.extend(items)

                    cursor = data.get(cursor_key)
                    page_count += 1

                    if not cursor:
                        break

                return {items_key: all_items}

            elif pag_type == "next_url":
                next_key = pagination.get("next_key", "next")
                items_key = pagination.get("items_key", "items")

                current_url = url

                while page_count < max_pages:
                    data = await self._fetch_page(client, current_url, method, headers, json_body=json_body)

                    items = data.get(items_key, [])
                    all_items.extend(items)

                    current_url = data.get(next_key)
                    page_count += 1

                    if not current_url:
                        break

                return {items_key: all_items}

        raise ValueError(f"Unknown pagination type: {pag_type}")

    async def fetch_data(
        self,
        config: Dict[str, Any],
        execution_id: str
    ) -> Path:
        """
        Ejecuta fetch de API y guarda resultado en archivo.

        Args:
            config: Configuración de la API
            execution_id: ID de ejecución para nombrar archivo

        Returns:
            Path al archivo guardado
        """
        data = await self._fetch_with_pagination(config)

        # Guardar respuesta
        response_format = config.get("response_format", "json")

        if response_format == "json":
            output_path = self.input_dir / f"{execution_id}_api_response.json"
            output_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        elif response_format == "csv":
            import pandas as pd

            # Asumir que data tiene estructura {"items": [...]}
            items_key = config.get("pagination", {}).get("items_key", "items")
            items = data.get(items_key, [])

            df = pd.DataFrame(items)
            output_path = self.input_dir / f"{execution_id}_api_response.csv"
            df.to_csv(output_path, index=False)

        else:
            raise ValueError(f"Unsupported response format: {response_format}")

        # Trigger workflow si está configurado
        if self.workflow_engine and self.flow_id:
            await self.trigger_workflow(output_path)

        return output_path

    async def trigger_workflow(self, data_path: Path):
        """Lanza workflow con datos fetched"""
        context = {
            "input_file": str(data_path),
            "trigger": "api_watcher"
        }

        try:
            execution_id = await self.workflow_engine.execute_flow(
                flow_id=self.flow_id,
                context=context
            )
        except Exception:
            # Workflow trigger failed - silent handling
            pass
