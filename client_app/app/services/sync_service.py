
import logging
import uuid
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlmodel import select
from automatia_shared.enums import TaskStatus

from client_app.app.database.db import get_db
from client_app.app.database.models import RunManifestLog, ServerConnection
from client_app.app.clients.brain_client import BrainAPIClient

logger = logging.getLogger(__name__)

class SyncService:
    """
    Servicio de sincronización de telemetría y logs con el servidor.
    Implementa Prompt 16 (Client Telemetry).
    """

    async def log_run_manifest(
        self,
        execution_id: str,
        service_id: str,
        model_used: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> RunManifestLog:
        """
        Registra una ejecución de IA en la base de datos local.
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())

        # Calcular totales
        total_tokens = prompt_tokens + completion_tokens

        log_entry = RunManifestLog(
            execution_id=execution_id,
            service_id=service_id,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            is_synced=False,
            created_at=datetime.utcnow()
        )

        try:
            async with get_db() as session:
                # Obtener client_id si está disponible (license key o configurado)
                # Por ahora lo dejamos None o placeholder
                # Podríamos buscar el ServerConnection para el client_id/license
                
                # Fetch license key for client_id context if needed
                # result = await session.exec(select(ServerConnection))
                # conn = result.first()
                # if conn:
                #     log_entry.client_id = conn.license_key # Use license as ID proxy?
                
                session.add(log_entry)
                await session.commit()
                await session.refresh(log_entry)
                logger.debug(f"[Telemetry] Logged run {execution_id} ({total_tokens} tokens)")
                return log_entry
        except Exception as e:
            logger.error(f"[Telemetry] Error logging run manifest: {e}")
            return None

    async def sync_manifests_to_server(self, batch_size: int = 50):
        """
        Envía logs pendientes al servidor en lotes.
        Llamado por Scheduler o al cerrar sesión.
        """
        logger.info("[Telemetry] Starting synchronization...")
        
        async with get_db() as session:
            # 1. Obtener logs no sincronizados
            statement = select(RunManifestLog).where(RunManifestLog.is_synced == False).limit(batch_size)
            results = await session.exec(statement)
            pending_logs = results.all()

            if not pending_logs:
                logger.info("[Telemetry] No pending logs to sync.")
                return

            # 2. Obtener configuración de conexión para URL y licencia
            conn_result = await session.exec(select(ServerConnection))
            server_conn = conn_result.first()
            
            if not server_conn or not server_conn.is_active:
                logger.warning("[Telemetry] No active server connection. Skipping sync.")
                return

            # Actualizar cliente con URL real
            client = BrainAPIClient(base_url=server_conn.brain_url)
            
            # 3. Preparar payload
            payload = [
                {
                    "execution_id": log.execution_id,
                    "service_id": log.service_id,
                    "model_used": log.model_used,
                    "prompt_tokens": log.prompt_tokens,
                    "completion_tokens": log.completion_tokens,
                    "total_tokens": log.total_tokens,
                    "duration_ms": log.duration_ms,
                    "status": log.status,
                    "error_message": log.error_message,
                    "timestamp": log.created_at.isoformat(),
                    # client_id se inyecta en el servidor via license key o se manda explícito
                }
                for log in pending_logs
            ]

            try:
                # 4. Enviar al servidor
                # Endpoint: POST /api/v1/telemetry/sync (Prompt 17 defines Server Endpoint)
                # Usamos post_generic ya que no es un método core del BrainClient todavía
                response = await client.post_generic(
                    endpoint="/api/v1/telemetry/sync",
                    json_data={"logs": payload},
                    license_key=server_conn.license_key
                )
                
                # 5. Marcar como sincronizados
                if response.get("status") == "success" or response.get("synced_count", 0) > 0:
                    for log in pending_logs:
                        log.is_synced = True
                        log.synced_at = datetime.utcnow()
                        session.add(log)
                    
                    await session.commit()
                    logger.info(f"[Telemetry] Successfully synced {len(pending_logs)} logs.")
                else:
                    logger.warning(f"[Telemetry] Sync response indicated failure: {response}")

            except Exception as e:
                logger.error(f"[Telemetry] Sync failed: {e}")

# Singleton instance
sync_service = SyncService()
