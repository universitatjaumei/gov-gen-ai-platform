# client_app/app/modules/output/http_connector.py
import httpx
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential


class HttpConnectorService:
    """
    Conector HTTP robusto para envio de datos.

    Features:
    - Reintentos con backoff exponencial
    - Soporte JSON, form-data, multipart
    - Logging en TaskLog para trazabilidad
    - Autenticacion (Bearer, Basic, API Key)
    - Timeout configurable
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout: float = 30.0,
        task_log_session=None,
        execution_id: Optional[str] = None
    ):
        """
        Args:
            max_retries: Numero maximo de reintentos
            timeout: Timeout en segundos
            task_log_session: Sesion SQLModel para logging
            execution_id: ID de ejecucion para TaskLog
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.task_log_session = task_log_session
        self.execution_id = execution_id

    def _build_headers(
        self,
        auth: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Construye headers con autenticacion"""
        headers = {
            "User-Agent": "GovGenAI-HttpConnector/1.0"
        }

        if extra_headers:
            headers.update(extra_headers)

        if not auth:
            return headers

        auth_type = auth.get("type")

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {auth['token']}"
        elif auth_type == "basic":
            import base64
            creds = f"{auth['user']}:{auth['password']}"
            encoded = base64.b64encode(creds.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        elif auth_type == "api_key":
            header_name = auth.get("header", "X-API-Key")
            headers[header_name] = auth["key"]

        return headers

    def _log_to_task_log(
        self,
        url: str,
        method: str,
        status: str,
        status_code: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Registra la operacion en TaskLog"""
        if not self.task_log_session or not self.execution_id:
            return

        from client_app.app.database.models import TaskLog

        # Extraer dominio de la URL para step_name
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

        log = TaskLog(
            execution_id=self.execution_id,
            step_index=0,
            step_name=f"HTTP {method} to {domain}",
            status=status,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow() if status in ["success", "failed"] else None,
            result_summary=f"Status code: {status_code}" if status_code else None,
            error_message=error
        )

        self.task_log_session.add(log)
        self.task_log_session.commit()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def send_json(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
        auth: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Envia datos JSON via HTTP con reintentos.

        Args:
            method: HTTP method (POST, PUT, PATCH)
            url: URL destino
            payload: Datos JSON a enviar
            auth: Configuracion de autenticacion
            headers: Headers adicionales

        Returns:
            Respuesta parseada como dict

        Raises:
            Exception: Si falla despues de todos los reintentos
        """
        request_headers = self._build_headers(auth, headers)
        request_headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "POST":
                    response = await client.post(
                        url,
                        json=payload,
                        headers=request_headers,
                        timeout=self.timeout
                    )
                elif method.upper() == "PUT":
                    response = await client.put(
                        url,
                        json=payload,
                        headers=request_headers,
                        timeout=self.timeout
                    )
                elif method.upper() == "PATCH":
                    response = await client.patch(
                        url,
                        json=payload,
                        headers=request_headers,
                        timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported method: {method}")

                response.raise_for_status()

                result = response.json()

                # Log success
                self._log_to_task_log(
                    url=url,
                    method=method,
                    status="success",
                    status_code=response.status_code
                )

                return result

        except Exception as e:
            # Log failure
            self._log_to_task_log(
                url=url,
                method=method,
                status="failed",
                error=str(e)
            )
            raise

    async def send_form_data(
        self,
        url: str,
        data: Dict[str, str],
        auth: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Envia form-data (application/x-www-form-urlencoded)"""
        headers = self._build_headers(auth)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )

                response.raise_for_status()
                result = response.json()

                self._log_to_task_log(
                    url=url,
                    method="POST",
                    status="success",
                    status_code=response.status_code
                )

                return result

        except Exception as e:
            self._log_to_task_log(
                url=url,
                method="POST",
                status="failed",
                error=str(e)
            )
            raise

    async def send_multipart(
        self,
        url: str,
        files: Dict[str, Path],
        data: Optional[Dict[str, str]] = None,
        auth: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Envia multipart/form-data con archivos.

        Args:
            url: URL destino
            files: Dict de {field_name: file_path}
            data: Campos adicionales de texto
            auth: Autenticacion
        """
        headers = self._build_headers(auth)
        files_payload = {}

        try:
            # Preparar archivos para httpx
            for field_name, file_path in files.items():
                files_payload[field_name] = open(file_path, 'rb')

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    files=files_payload,
                    data=data or {},
                    headers=headers,
                    timeout=self.timeout
                )

                response.raise_for_status()
                result = response.json()

                self._log_to_task_log(
                    url=url,
                    method="POST",
                    status="success",
                    status_code=response.status_code
                )

                return result

        except Exception as e:
            self._log_to_task_log(
                url=url,
                method="POST",
                status="failed",
                error=str(e)
            )
            raise

        finally:
            # Cerrar archivos abiertos
            for f in files_payload.values():
                f.close()
