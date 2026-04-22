from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import ClientTelemetryLog
from server.app.services.ai_brain import AIBrainService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/telemetry",
    tags=["telemetry"]
)

class TelemetryLogDTO(BaseModel):
    execution_id: str
    service_id: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int
    status: str
    error_message: Optional[str] = None
    timestamp: datetime

class TelemetrySyncRequest(BaseModel):
    logs: List[TelemetryLogDTO]

async def get_session() -> AsyncSession:
    async with AsyncSession(server_engine) as session:
        yield session

@router.post("/sync")
async def sync_telemetry(
    request: TelemetrySyncRequest,
    x_license_key: str = Header(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Recibe un lote de logs de ejecución desde el cliente y los persiste.
    """
    brain_service = AIBrainService()
    try:
        # Validate license and get client
        # _validate_license returns a License model which has client_id
        license_obj = await brain_service._validate_license(x_license_key)
        client_id = license_obj.client_id
        
        new_logs = []
        for log_dto in request.logs:
            # Map DTO to DB Model
            # We use service_id as script_hash proxy for now, or we could leave it generic
            db_log = ClientTelemetryLog(
                client_id=client_id,
                machine_id="unknown", # Client not sending this yet
                manifest_id=log_dto.execution_id,
                script_hash=log_dto.service_id, 
                execution_time_ms=log_dto.duration_ms,
                total_tokens=log_dto.total_tokens,
                cost_estimated=0.0, # Calculation deferred
                status=log_dto.status,
                error_message=log_dto.error_message,
                timestamp_client=log_dto.timestamp,
                synced_at=datetime.utcnow()
            )
            new_logs.append(db_log)
            session.add(db_log)
        
        await session.commit()
        
        logger.info(f"Synced {len(new_logs)} telemetry logs from client {client_id}")
        
        return {
            "status": "success",
            "synced_count": len(new_logs)
        }

    except ValueError as e:
        logger.warning(f"Telemetry sync auth failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing telemetry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
