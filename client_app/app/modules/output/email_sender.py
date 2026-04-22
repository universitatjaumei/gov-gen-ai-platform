# client_app/app/modules/output/email_sender.py
"""
Email sending service with encrypted credentials.

Sends emails (text/HTML) with attachments using SMTP.
Credentials are encrypted using EncryptionService for security.
"""
import smtplib
from email.message import EmailMessage
from typing import List, Optional, Dict, Any
from pathlib import Path


class EmailSender:
    """
    Servicio de envio de emails con credenciales cifradas.

    Features:
    - Envio de texto plano y HTML
    - Adjuntos de archivos
    - Credenciales SMTP cifradas con EncryptionService
    - Retorno de Message-ID para tracking
    - Manejo de errores de autenticacion
    """

    def __init__(
        self,
        smtp_credentials: Dict[str, Any],
        encryption_service=None
    ):
        """
        Args:
            smtp_credentials: {
                "server": "smtp.gmail.com",
                "port": 587,
                "username": "user@example.com",
                "password_encrypted": str  # Cifrado con EncryptionService
            }
            encryption_service: Instancia de EncryptionService
        """
        self.smtp_credentials = smtp_credentials
        self.encryption_service = encryption_service

    def _get_smtp_password(self) -> str:
        """Descifra la contrasena SMTP"""
        if "password_encrypted" in self.smtp_credentials:
            encrypted = self.smtp_credentials["password_encrypted"]

            if self.encryption_service:
                # EncryptionService devuelve un dict, extraemos "password"
                decrypted_data = self.encryption_service.decrypt(encrypted)
                return decrypted_data.get("password", "")
            else:
                # Fallback: asumir que esta en texto plano (solo dev)
                return encrypted

        # Fallback: password en texto plano (legacy)
        return self.smtp_credentials.get("password", "")

    def _build_message(
        self,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        body: str,
        html: bool = False,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> EmailMessage:
        """
        Construye el mensaje de email.

        Args:
            from_addr: Remitente
            to_addrs: Lista de destinatarios
            subject: Asunto
            body: Cuerpo del mensaje
            html: Si True, body es HTML
            attachments: Lista de {data: bytes, name: str}
            cc: Lista de CC
            bcc: Lista de BCC

        Returns:
            EmailMessage listo para enviar
        """
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)

        # Cuerpo del mensaje
        if html:
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)

        # Adjuntos
        for attachment in attachments or []:
            data = attachment["data"]
            name = attachment.get("name", "attachment.bin")

            msg.add_attachment(
                data,
                maintype="application",
                subtype="octet-stream",
                filename=name
            )

        return msg

    def send(
        self,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        body: str,
        html: bool = False,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> str:
        """
        Envia un email via SMTP.

        Args:
            Ver _build_message()

        Returns:
            Message-ID del email enviado

        Raises:
            Exception: Si falla autenticacion o envio
        """
        msg = self._build_message(
            from_addr, to_addrs, subject, body,
            html, attachments, cc, bcc
        )

        # Configuracion SMTP
        server = self.smtp_credentials.get("server")
        port = self.smtp_credentials.get("port", 587)
        username = self.smtp_credentials.get("username")
        password = self._get_smtp_password()

        # Enviar
        with smtplib.SMTP(server, port, timeout=30) as smtp:
            smtp.starttls()

            if username and password:
                smtp.login(username, password)

            smtp.send_message(msg)

        # Retornar Message-ID para tracking
        return msg.get("Message-Id", "")

    def send_with_file_attachments(
        self,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        body: str,
        file_paths: List[Path],
        html: bool = False
    ) -> str:
        """
        Envia email con archivos adjuntos desde rutas.

        Args:
            file_paths: Lista de rutas a archivos
        """
        # Leer archivos
        attachments = []
        for file_path in file_paths:
            attachments.append({
                "data": file_path.read_bytes(),
                "name": file_path.name
            })

        return self.send(
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject=subject,
            body=body,
            html=html,
            attachments=attachments
        )
