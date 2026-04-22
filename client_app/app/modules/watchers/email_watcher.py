from imapclient import IMAPClient
from email import message_from_bytes
from email.message import Message
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import uuid

from client_app.app.services.event_bus_service import event_bus_service
from client_app.app.services.email_body_utils import extract_email_body, get_message_id
from client_app.app.services.received_emails_service import received_emails_service
from shared.automatia_shared.dtos import MailWatcherPayload, TriggerPayloadMeta

class EmailWatcher:
    """
    Monitor de buzón IMAP con whitelist y emisión de eventos.
    
    Features:
    - Whitelist de remitentes (regex)
    - Descarga de adjuntos a execution_dir/input
    - Sanitización de nombres de archivo
    - Emisión de eventos a EventBus
    - Manejo de duplicados (nombres de archivo)
    """
    
    def __init__(
        self,
        credentials: Dict[str, str],
        path_manager,
        trigger_id: Optional[int] = None,
        workflow_engine=None,
        flow_id: Optional[str] = None,
        whitelist_senders: Optional[List[str]] = None,
        subject_filter: Optional[str] = None,
        folder: str = "INBOX",
        check_interval: int = 60
    ):
        """
        Args:
            credentials: {"server": "imap.example.com", "user": "...", "pass": "..."}
            path_manager: Instancia de ExecutionPathManager
            trigger_id: ID del TriggerConfig (Nuevo modo)
            workflow_engine: Instancia de WorkflowEngine (Modo Legacy)
            flow_id: ID del flujo a ejecutar (Modo Legacy)
            whitelist_senders: Lista de emails permitidos
            subject_filter: Filtro de asunto
            folder: Carpeta IMAP
            check_interval: Intervalo de chequeo
        """
        self.credentials = credentials
        self.path_manager = path_manager
        self.trigger_id = trigger_id
        self.workflow_engine = workflow_engine
        self.flow_id = flow_id
        self.whitelist = set(whitelist_senders or [])
        self.subject_filter = subject_filter.strip() if subject_filter else None
        self.folder = folder
        self.check_interval = check_interval
        self.client: Optional[IMAPClient] = None
        self.input_dir = None

    # ... (methods unchanged) ...

    async def process_email(self, email: Dict[str, Any]):
        """
        Procesa un email: descarga adjuntos, persiste en BD y emite evento.
        """
        sender = email['sender']
        subject = email.get('subject', '')

        # Verificar whitelist de remitentes
        if not self.is_sender_allowed(sender):
            return

        # Verificar filtro de asunto
        if not self.is_subject_allowed(subject):
            return

        # 1. Crear ID de ejecución
        execution_id = uuid.uuid4().hex

        # 2. Setup Input Dir
        execution_id = self.path_manager.create_run("EMAIL_TRIGGER")
        input_dir = self.path_manager.get_input_dir(execution_id)

        # Extraer cuerpo del email (si hay mensaje raw disponible)
        email_body_plain = email.get('body_plain', '')
        email_body_html = email.get('body_html')
        email_date = email.get('date', datetime.utcnow())
        message_id = email.get('msg_id', '')

        saved_attachments = []
        primary_attachment = None
        attachments_info = []

        for att in email['attachments']:
            fname = self._sanitize_filename(att['filename'])
            file_path = input_dir / fname

            # Guardar archivo
            file_path.write_bytes(att['data'])
            saved_attachments.append(str(file_path))
            attachments_info.append({
                "filename": fname,
                "path": str(file_path),
                "size": len(att['data'])
            })
            if not primary_attachment:
                primary_attachment = str(file_path)

            # Legacy Direct Execution (per attachment, matching old behavior roughly)
            if self.flow_id and self.workflow_engine:
                 await self.trigger_workflow_legacy(file_path, sender, execution_id)

        print(f"[EmailWatcher] Processed email from {sender}, saved {len(saved_attachments)} attachments.")

        # Persistir email en base de datos (con deduplicación)
        if message_id:
            await received_emails_service.save_email(
                message_id=message_id,
                source="watcher",
                sender=sender,
                subject=subject,
                email_date=email_date if isinstance(email_date, datetime) else datetime.utcnow(),
                body_plain=email_body_plain,
                body_html=email_body_html,
                attachments_info=attachments_info
            )

        # New Event Bus Mode (Emit one event per email, with list of attachments)
        if self.trigger_id is not None:
            # 3. Construct Payload
            meta = TriggerPayloadMeta(
                trigger_id=self.trigger_id,
                trigger_type="mail_watcher",
                timestamp=datetime.utcnow(),
                execution_id=execution_id
            )

            payload = MailWatcherPayload(
                meta=meta,
                data={
                    "sender": sender,
                    "subject": subject,
                    "attachments": saved_attachments,
                    "primary_attachment": primary_attachment,
                    "email_msg_id": message_id,
                    "email_body_plain": email_body_plain,
                    "email_body_html": email_body_html
                }
            )

            # 4. Emit Event
            await event_bus_service.emit_trigger_event(
                trigger_id=self.trigger_id,
                payload=payload.model_dump()
            )

    async def trigger_workflow_legacy(self, file_path: Path, sender: str, execution_id: Optional[str] = None):
        """
        Lanza el workflow configurado usando el motor (Legacy Mode).
        """
        try:
            # 1. Recuperar definición del flujo desde la BD
            flow = None
            async with AsyncSession(client_engine) as session:
                flow = await session.get(FlowRegistry, self.flow_id)
                
            if not flow:
                print(f"[EmailWatcher] Error: Flow {self.flow_id} not found in registry")
                return

            # 2. Convertir ORM a FlowSpec
            steps_data = json.loads(flow.steps) if isinstance(flow.steps, str) else flow.steps
            trigger_config_data = json.loads(flow.trigger_config) if isinstance(flow.trigger_config, str) else flow.trigger_config
            
            flow_spec = FlowSpec(
                name=flow.name,
                description=flow.description,
                version=flow.version,
                status=flow.status,
                row_version=flow.row_version,
                trigger_type=flow.trigger_type,
                trigger_config=trigger_config_data or {},
                steps=steps_data or [],
                is_active=flow.is_active,
                owner_scope=flow.owner_scope
            )
            
            # 3. Ejecutar workflow
            await self.workflow_engine.execute_flow(
                flow_spec,
                context={
                    "trigger": "email", 
                    "sender": sender,
                    "input_file": str(file_path)
                },
                execution_id=execution_id
            )
        except Exception as e:
                print(f"[EmailWatcher] Legacy Trigger Error: {e}")
