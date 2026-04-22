"""
Servicio para loguear eventos de conexiones.
"""
from datetime import datetime
from typing import Optional
from client_app.app.core.state import state
from client_app.app.database.models import ConnectionLog


async def log_connection_event(
    connection_type: str,
    connection_name: str,
    event_type: str,
    status: str,
    message: str,
    details: Optional[str] = None
) -> ConnectionLog:
    """
    Crea un registro de log para evento de conexión.

    Args:
        connection_type: Tipo de conexión ('email', 'web', 'file', 'api')
        connection_name: Nombre descriptivo de la conexión
        event_type: Tipo de evento ('connect', 'disconnect', 'error', 'trigger', 'poll')
        status: Estado del evento ('success', 'error', 'warning', 'info')
        message: Mensaje descriptivo
        details: JSON con detalles adicionales (opcional)

    Returns:
        ConnectionLog creado
    """
    log = ConnectionLog(
        timestamp=datetime.utcnow(),
        connection_type=connection_type,
        connection_name=connection_name,
        event_type=event_type,
        status=status,
        message=message,
        details=details
    )

    async with state.db_session() as session:
        session.add(log)
        await session.commit()
        await session.refresh(log)

    return log


async def log_email_trigger(connection_name: str, sender: str, subject: str) -> ConnectionLog:
    """Shortcut para loguear email recibido."""
    return await log_connection_event(
        connection_type='email',
        connection_name=connection_name,
        event_type='trigger',
        status='success',
        message=f"Email recibido de {sender}: {subject[:50]}"
    )


async def log_web_change(connection_name: str, url: str, change_summary: str) -> ConnectionLog:
    """Shortcut para loguear cambio web detectado."""
    return await log_connection_event(
        connection_type='web',
        connection_name=connection_name,
        event_type='trigger',
        status='success',
        message=f"Cambio detectado: {change_summary[:100]}"
    )


async def log_connection_error(connection_type: str, connection_name: str, error_msg: str) -> ConnectionLog:
    """Shortcut para loguear error de conexión."""
    return await log_connection_event(
        connection_type=connection_type,
        connection_name=connection_name,
        event_type='error',
        status='error',
        message=error_msg
    )
