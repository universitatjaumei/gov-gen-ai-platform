"""
EmailScanService - Recolección Pasiva de Emails para Flujos

Servicio para buscar correos por criterio y descargar adjuntos.
A diferencia del EmailWatcher (monitoreo continuo), este servicio
realiza un escaneo puntual bajo demanda.

Funcionalidades:
- Búsqueda por criterios (asunto, remitente, fecha, etc.)
- Descarga de adjuntos a carpeta temporal
- Generación de Data Pills tipo FILE[] para encadenar con otros átomos
"""

import os
import email
import imaplib
import asyncio
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime

from client_app.app.database.db import client_engine
from client_app.app.database.models import LocalCredentials
from client_app.app.services.enterprise_audit_service import enterprise_audit_service
from client_app.app.services.file_system_service import FileInfo
from client_app.app.services.email_body_utils import extract_email_body, get_message_id
from client_app.app.services.received_emails_service import received_emails_service
from client_app.app.core.hardware_fingerprint import get_machine_fingerprint
from client_app.app.modules.security.encryption_service import EncryptionService
from automatia_shared.core.audit_models import RiskLevel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


@dataclass
class EmailSearchCriteria:
    """Criterios de búsqueda de emails."""
    subject_contains: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    since_date: Optional[datetime] = None
    before_date: Optional[datetime] = None
    has_attachments: bool = False
    folder: str = "INBOX"
    max_emails: int = 50
    mark_as_read: bool = False

    def to_imap_search(self) -> str:
        """Convierte criterios a comando IMAP SEARCH."""
        criteria = []

        if self.subject_contains:
            # Escapar comillas
            subject = self.subject_contains.replace('"', '\\"')
            criteria.append(f'SUBJECT "{subject}"')

        if self.from_address:
            criteria.append(f'FROM "{self.from_address}"')

        if self.to_address:
            criteria.append(f'TO "{self.to_address}"')

        if self.since_date:
            date_str = self.since_date.strftime("%d-%b-%Y")
            criteria.append(f'SINCE {date_str}')

        if self.before_date:
            date_str = self.before_date.strftime("%d-%b-%Y")
            criteria.append(f'BEFORE {date_str}')

        if not criteria:
            criteria.append("ALL")

        return " ".join(criteria)


@dataclass
class EmailAttachment:
    """Información de un adjunto descargado."""
    filename: str
    path: str
    content_type: str
    size_bytes: int

    def to_file_info(self) -> FileInfo:
        """Convierte a FileInfo para compatibilidad con FileSystemService."""
        return FileInfo(
            path=self.path,
            name=self.filename,
            extension=Path(self.filename).suffix.lower(),
            size_bytes=self.size_bytes,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            is_directory=False
        )


@dataclass
class ScannedEmail:
    """Información de un email escaneado."""
    uid: str
    subject: str
    from_address: str
    to_address: str
    date: datetime
    body_text: str
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para Data Pills."""
        return {
            "uid": self.uid,
            "subject": self.subject,
            "from": self.from_address,
            "to": self.to_address,
            "date": self.date.isoformat() if self.date else None,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "attachments": [
                {"filename": a.filename, "path": a.path, "size": a.size_bytes}
                for a in self.attachments
            ],
            "has_attachments": len(self.attachments) > 0,
            "attachment_count": len(self.attachments),
        }


@dataclass
class EmailScanResult:
    """Resultado de un escaneo de emails."""
    success: bool
    emails: List[ScannedEmail] = field(default_factory=list)
    total_emails: int = 0
    total_attachments: int = 0
    attachments: List[FileInfo] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para output contract."""
        return {
            "success": self.success,
            "emails": [e.to_dict() for e in self.emails],
            "total_emails": self.total_emails,
            "total_attachments": self.total_attachments,
            "attachments": [a.to_dict() for a in self.attachments],
            "error": self.error,
        }


class EmailScanService:
    """
    Servicio para escaneo puntual de emails y descarga de adjuntos.

    A diferencia del EmailWatcher que monitorea continuamente,
    este servicio realiza una búsqueda bajo demanda cuando se
    ejecuta como parte de un flujo.
    """

    # Directorio temporal para adjuntos
    TEMP_DIR = Path(tempfile.gettempdir()) / "automatia" / "email_attachments"

    def __init__(self):
        self._audit_enabled = True
        self._encryption_service = EncryptionService()

    async def _get_credentials(self, connection_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene y desencripta credenciales de una conexión EMAIL.

        Args:
            connection_id: ID del átomo CONNECTION de tipo EMAIL

        Returns:
            Diccionario con credenciales desencriptadas o None
        """
        try:
            from client_app.app.services.mail_watcher_service import mail_watcher_service
            return await mail_watcher_service.get_credential(connection_id)
        except Exception as e:
            print(f"[EmailScanService] Error obteniendo credenciales: {e}")
            return None

    def _decode_header_value(self, value: str) -> str:
        """Decodifica un header de email que puede tener encoding."""
        if not value:
            return ""

        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                charset = charset or "utf-8"
                try:
                    result.append(part.decode(charset, errors="replace"))
                except:
                    result.append(part.decode("utf-8", errors="replace"))
            else:
                result.append(str(part))

        return "".join(result)

    def _get_email_body(self, msg: email.message.Message) -> tuple[str, Optional[str]]:
        """Extrae el cuerpo del email (texto plano y HTML).

        Delegado a email_body_utils para centralizar la lógica.
        """
        return extract_email_body(msg)

    async def _download_attachments(
        self,
        msg: email.message.Message,
        email_uid: str,
        download_path: Path
    ) -> List[EmailAttachment]:
        """Descarga adjuntos de un email a disco."""
        attachments = []

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = self._decode_header_value(filename)

                    # Sanitizar nombre de archivo
                    filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
                    if not filename:
                        filename = f"attachment_{email_uid}_{len(attachments)}"

                    # Crear subdirectorio por email
                    email_dir = download_path / email_uid
                    email_dir.mkdir(parents=True, exist_ok=True)

                    filepath = email_dir / filename
                    payload = part.get_payload(decode=True)

                    if payload:
                        # Escribir archivo en thread pool
                        def write_file():
                            with open(filepath, "wb") as f:
                                f.write(payload)
                            return len(payload)

                        size = await asyncio.get_event_loop().run_in_executor(
                            None, write_file
                        )

                        attachments.append(EmailAttachment(
                            filename=filename,
                            path=str(filepath),
                            content_type=part.get_content_type(),
                            size_bytes=size
                        ))

        return attachments

    async def scan_emails(
        self,
        connection_id: int,
        criteria: EmailSearchCriteria,
        download_attachments: bool = True,
        download_path: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        flow_id: Optional[int] = None,
        execution_id: Optional[str] = None,
        persist_to_db: bool = True,
    ) -> EmailScanResult:
        """
        Escanea emails según criterios y opcionalmente descarga adjuntos.

        Args:
            connection_id: ID de la conexión EMAIL a usar
            criteria: Criterios de búsqueda
            download_attachments: Si True, descarga adjuntos
            download_path: Ruta donde guardar adjuntos (None = temporal)
            variables: Variables para resolver en criterios
            flow_id: ID del flujo (para auditoría)
            execution_id: ID de ejecución (para auditoría)
            persist_to_db: Si True, guarda emails en BD para informes/LLM

        Returns:
            EmailScanResult con emails encontrados y adjuntos
        """
        # Resolver variables en criterios
        if variables and criteria.subject_contains:
            for key, value in variables.items():
                placeholder = "{{" + key + "}}"
                criteria.subject_contains = criteria.subject_contains.replace(
                    placeholder, str(value)
                )

        # Obtener credenciales
        creds = await self._get_credentials(connection_id)
        if not creds:
            return EmailScanResult(
                success=False,
                error=f"No se encontraron credenciales para connection_id={connection_id}"
            )

        # Determinar ruta de descarga
        if download_path:
            dl_path = Path(download_path)
        else:
            dl_path = self.TEMP_DIR / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        dl_path.mkdir(parents=True, exist_ok=True)

        try:
            # Conectar a IMAP en thread pool
            def connect_imap():
                host = creds.get("host", "")
                port = creds.get("port", 993)
                use_ssl = creds.get("use_ssl", True)

                if use_ssl:
                    mail = imaplib.IMAP4_SSL(host, port)
                else:
                    mail = imaplib.IMAP4(host, port)

                mail.login(creds["username"], creds["password"])
                return mail

            mail = await asyncio.get_event_loop().run_in_executor(
                None, connect_imap
            )

            # Seleccionar carpeta
            def select_folder():
                return mail.select(criteria.folder)

            status, _ = await asyncio.get_event_loop().run_in_executor(
                None, select_folder
            )

            if status != "OK":
                return EmailScanResult(
                    success=False,
                    error=f"No se pudo seleccionar carpeta: {criteria.folder}"
                )

            # Buscar emails
            search_cmd = criteria.to_imap_search()

            def search_emails():
                return mail.search(None, search_cmd)

            status, data = await asyncio.get_event_loop().run_in_executor(
                None, search_emails
            )

            if status != "OK":
                return EmailScanResult(
                    success=False,
                    error=f"Error en búsqueda IMAP: {search_cmd}"
                )

            email_ids = data[0].split()
            # Limitar cantidad y tomar los más recientes
            email_ids = email_ids[-criteria.max_emails:]

            scanned_emails: List[ScannedEmail] = []
            all_attachments: List[FileInfo] = []

            for email_id in email_ids:
                def fetch_email():
                    return mail.fetch(email_id, "(RFC822)")

                status, msg_data = await asyncio.get_event_loop().run_in_executor(
                    None, fetch_email
                )

                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extraer información
                uid = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                subject = self._decode_header_value(msg.get("Subject", ""))
                from_addr = self._decode_header_value(msg.get("From", ""))
                to_addr = self._decode_header_value(msg.get("To", ""))

                # Parsear fecha
                date_str = msg.get("Date", "")
                try:
                    email_date = parsedate_to_datetime(date_str)
                except:
                    email_date = datetime.now()

                # Extraer cuerpo
                body_text, body_html = self._get_email_body(msg)

                # Filtrar por adjuntos si se requiere
                has_attachments_flag = any(
                    "attachment" in str(part.get("Content-Disposition", ""))
                    for part in msg.walk()
                )

                if criteria.has_attachments and not has_attachments_flag:
                    continue

                # Descargar adjuntos
                attachments = []
                if download_attachments and has_attachments_flag:
                    attachments = await self._download_attachments(msg, uid, dl_path)
                    all_attachments.extend([a.to_file_info() for a in attachments])

                scanned_emails.append(ScannedEmail(
                    uid=uid,
                    subject=subject,
                    from_address=from_addr,
                    to_address=to_addr,
                    date=email_date,
                    body_text=body_text,
                    body_html=body_html,
                    attachments=attachments
                ))

                # Persistir en base de datos (con deduplicación por message_id)
                if persist_to_db:
                    message_id = get_message_id(msg)
                    attachments_info = [
                        {"filename": a.filename, "path": a.path, "size": a.size_bytes}
                        for a in attachments
                    ]
                    await received_emails_service.save_email(
                        message_id=message_id,
                        source="scan",
                        sender=from_addr,
                        subject=subject,
                        email_date=email_date,
                        body_plain=body_text,
                        body_html=body_html,
                        attachments_info=attachments_info
                    )

                # Marcar como leído si se solicita
                if criteria.mark_as_read:
                    def mark_read():
                        mail.store(email_id, "+FLAGS", "\\Seen")
                    await asyncio.get_event_loop().run_in_executor(None, mark_read)

            # Cerrar conexión
            def close_connection():
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass

            await asyncio.get_event_loop().run_in_executor(None, close_connection)

            result = EmailScanResult(
                success=True,
                emails=scanned_emails,
                total_emails=len(scanned_emails),
                total_attachments=len(all_attachments),
                attachments=all_attachments
            )

            # Auditoría
            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="EMAIL_SCAN_EXECUTED",
                    module="email_scan_service",
                    source_description=f"IMAP folder: {criteria.folder}",
                    target_description=f"Search: {search_cmd}",
                    risk_level=RiskLevel.LOW.value,
                    execution_id=execution_id,
                    additional_context={
                        "connection_id": connection_id,
                        "emails_found": len(scanned_emails),
                        "attachments_downloaded": len(all_attachments),
                        "flow_id": flow_id,
                    }
                )

            return result

        except imaplib.IMAP4.error as e:
            return EmailScanResult(
                success=False,
                error=f"Error IMAP: {str(e)}"
            )
        except Exception as e:
            return EmailScanResult(
                success=False,
                error=f"Error inesperado: {str(e)}"
            )

    async def test_connection(self, connection_id: int) -> tuple[bool, str]:
        """
        Prueba la conexión IMAP sin descargar emails.

        Args:
            connection_id: ID de la conexión EMAIL

        Returns:
            Tupla (success, message)
        """
        creds = await self._get_credentials(connection_id)
        if not creds:
            return False, "Credenciales no encontradas"

        try:
            def test_imap():
                host = creds.get("host", "")
                port = creds.get("port", 993)
                use_ssl = creds.get("use_ssl", True)

                if use_ssl:
                    mail = imaplib.IMAP4_SSL(host, port)
                else:
                    mail = imaplib.IMAP4(host, port)

                mail.login(creds["username"], creds["password"])
                mail.select("INBOX")
                mail.close()
                mail.logout()
                return True

            await asyncio.get_event_loop().run_in_executor(None, test_imap)
            return True, "Conexión exitosa"

        except imaplib.IMAP4.error as e:
            return False, f"Error IMAP: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"


# Singleton
email_scan_service = EmailScanService()
