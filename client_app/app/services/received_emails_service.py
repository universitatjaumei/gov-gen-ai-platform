"""
ReceivedEmailsService - Servicio para consulta y gestión de correos recibidos.

Proporciona métodos para:
- Consultar correos por rango de fechas
- Filtrar por origen (watcher/scan)
- Marcar correos como procesados
- Construir contexto para LLM
"""
import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import ReceivedEmail
from client_app.app.services.email_body_utils import clean_email_body, build_llm_context


class ReceivedEmailsService:
    """Servicio para gestión de correos recibidos persistidos."""

    async def get_emails_by_date_range(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        source: Optional[str] = None,
        include_processed: bool = True,
        limit: int = 100
    ) -> List[ReceivedEmail]:
        """
        Obtiene correos filtrados por rango de fechas.

        Args:
            date_from: Fecha de inicio (inclusive). Por defecto: hoy
            date_to: Fecha de fin (inclusive). Por defecto: hoy
            source: Filtrar por origen ('watcher' o 'scan'). None = todos
            include_processed: Si incluir correos ya procesados
            limit: Número máximo de correos a devolver

        Returns:
            Lista de ReceivedEmail ordenados por fecha descendente
        """
        async with AsyncSession(client_engine) as session:
            stmt = select(ReceivedEmail)

            # Filtro de fechas
            if date_from:
                from_dt = datetime.combine(date_from, datetime.min.time())
                stmt = stmt.where(ReceivedEmail.date >= from_dt)

            if date_to:
                to_dt = datetime.combine(date_to, datetime.max.time())
                stmt = stmt.where(ReceivedEmail.date <= to_dt)

            # Filtro de origen
            if source:
                stmt = stmt.where(ReceivedEmail.source == source)

            # Filtro de procesados
            if not include_processed:
                stmt = stmt.where(ReceivedEmail.is_processed == False)

            # Ordenar por fecha descendente y limitar
            stmt = stmt.order_by(ReceivedEmail.date.desc()).limit(limit)

            result = await session.exec(stmt)
            return list(result.all())

    async def get_email_by_id(self, email_id: int) -> Optional[ReceivedEmail]:
        """Obtiene un correo por su ID."""
        async with AsyncSession(client_engine) as session:
            return await session.get(ReceivedEmail, email_id)

    async def get_email_by_message_id(self, message_id: str) -> Optional[ReceivedEmail]:
        """Obtiene un correo por su Message-ID (para deduplicación)."""
        async with AsyncSession(client_engine) as session:
            stmt = select(ReceivedEmail).where(ReceivedEmail.message_id == message_id)
            result = await session.exec(stmt)
            return result.first()

    async def save_email(
        self,
        message_id: str,
        source: str,
        sender: str,
        subject: str,
        email_date: datetime,
        body_plain: str,
        body_html: Optional[str] = None,
        attachments_info: Optional[List[Dict]] = None
    ) -> Optional[ReceivedEmail]:
        """
        Guarda un correo en la base de datos.
        Si ya existe un correo con el mismo message_id, no lo duplica.

        Args:
            message_id: ID único del mensaje IMAP
            source: Origen del correo ('watcher' o 'scan')
            sender: Dirección del remitente
            subject: Asunto del correo
            email_date: Fecha y hora del correo
            body_plain: Cuerpo en texto plano
            body_html: Cuerpo en HTML (opcional)
            attachments_info: Lista de dicts con info de adjuntos

        Returns:
            ReceivedEmail creado o None si ya existía
        """
        async with AsyncSession(client_engine) as session:
            # Verificar si ya existe
            existing = await self.get_email_by_message_id(message_id)
            if existing:
                return None

            # Crear nuevo registro
            email_record = ReceivedEmail(
                message_id=message_id,
                source=source,
                sender=sender,
                subject=subject,
                date=email_date,
                body_plain=body_plain,
                body_html=body_html,
                attachments_info=json.dumps(attachments_info or []),
                is_processed=False,
                created_at=datetime.utcnow()
            )

            session.add(email_record)
            await session.commit()
            await session.refresh(email_record)

            return email_record

    async def mark_as_processed(self, email_ids: List[int]) -> int:
        """
        Marca correos como procesados.

        Args:
            email_ids: Lista de IDs de correos a marcar

        Returns:
            Número de correos actualizados
        """
        if not email_ids:
            return 0

        async with AsyncSession(client_engine) as session:
            count = 0
            for email_id in email_ids:
                email_record = await session.get(ReceivedEmail, email_id)
                if email_record and not email_record.is_processed:
                    email_record.is_processed = True
                    session.add(email_record)
                    count += 1

            await session.commit()
            return count

    async def delete_email(self, email_id: int) -> bool:
        """Elimina un correo de la base de datos."""
        async with AsyncSession(client_engine) as session:
            email_record = await session.get(ReceivedEmail, email_id)
            if email_record:
                await session.delete(email_record)
                await session.commit()
                return True
            return False

    async def build_context_for_llm(
        self,
        email_ids: List[int],
        clean_bodies: bool = True,
        max_chars: int = 50000
    ) -> str:
        """
        Construye el contexto concatenado de múltiples correos para LLM.

        Args:
            email_ids: Lista de IDs de correos a incluir
            clean_bodies: Si aplicar limpieza (firmas, hilos) a los cuerpos
            max_chars: Límite máximo de caracteres

        Returns:
            Texto formateado listo para usar como contexto de LLM
        """
        if not email_ids:
            return ""

        emails_data = []

        async with AsyncSession(client_engine) as session:
            for email_id in email_ids:
                email_record = await session.get(ReceivedEmail, email_id)
                if email_record:
                    body = email_record.body_plain
                    if clean_bodies:
                        body = clean_email_body(body)

                    emails_data.append({
                        'sender': email_record.sender,
                        'subject': email_record.subject,
                        'date': email_record.date.strftime('%Y-%m-%d %H:%M'),
                        'body_plain': body
                    })

        return build_llm_context(emails_data, max_chars)

    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de correos recibidos."""
        async with AsyncSession(client_engine) as session:
            # Total de correos
            stmt_total = select(ReceivedEmail)
            result_total = await session.exec(stmt_total)
            all_emails = list(result_total.all())

            total = len(all_emails)
            processed = sum(1 for e in all_emails if e.is_processed)
            from_watcher = sum(1 for e in all_emails if e.source == 'watcher')
            from_scan = sum(1 for e in all_emails if e.source == 'scan')

            return {
                'total': total,
                'processed': processed,
                'pending': total - processed,
                'from_watcher': from_watcher,
                'from_scan': from_scan
            }


# Singleton
received_emails_service = ReceivedEmailsService()
