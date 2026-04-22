import functools
import logging
import time
import inspect
from typing import Any, Callable, Dict, Optional
from client_app.app.services.enterprise_audit_service import enterprise_audit_service
from client_app.app.database.models import RiskLevel

logger = logging.getLogger(__name__)

def audit_operation(action_type: str, module: str, risk_level: str = RiskLevel.LOW.value):
    """
    Decorador para auditar automáticamente operaciones en los servicios.
    Registra el inicio (opcionalmente) y el fin de la ejecución, incluyendo errores.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            execution_id = kwargs.get("execution_id")
            user_id = kwargs.get("user_id", "system")
            
            # Intentar extraer info útil de los argumentos
            source = kwargs.get("source") or kwargs.get("filename")
            if not source and args:
                # Si el primer argumento es self/cls, saltar al segundo
                idx = 1 if args and hasattr(args[0], '__dict__') else 0
                if len(args) > idx and isinstance(args[idx], str):
                    source = args[idx]

            try:
                result = await func(*args, **kwargs)
                
                duration = int((time.time() - start_time) * 1000)
                
                # Log de éxito
                await enterprise_audit_service.log_event(
                    action_type=action_type,
                    module=module,
                    user_id=user_id,
                    source_description=str(source) if source else None,
                    risk_level=risk_level,
                    execution_id=execution_id,
                    additional_context={
                        "duration_ms": duration,
                        "status": "success"
                    }
                )
                
                return result
                
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                
                # Log de error (Riesgo más alto si falla una operación auditada)
                error_risk = RiskLevel.HIGH.value if risk_level == RiskLevel.LOW.value else risk_level
                
                await enterprise_audit_service.log_event(
                    action_type=action_type,
                    module=module,
                    user_id=user_id,
                    source_description=str(source) if source else None,
                    risk_level=error_risk,
                    execution_id=execution_id,
                    additional_context={
                        "duration_ms": duration,
                        "status": "failed",
                        "error": str(e)
                    }
                )
                raise e
        return wrapper
    return decorator
