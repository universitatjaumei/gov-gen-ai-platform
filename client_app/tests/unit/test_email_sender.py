# client_app/tests/unit/test_email_sender.py
"""
Unit tests for EmailSender.

Tests verify:
- Message construction (plain text, HTML, attachments)
- Encrypted credential handling with EncryptionService
- SMTP error handling
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.modules.output.email_sender import EmailSender


def test_build_message_minimal():
    """Verificar construccion de mensaje basico"""
    sender = EmailSender(smtp_credentials={})

    msg = sender._build_message(
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
        subject="Test Subject",
        body="Test Body"
    )

    msg_str = msg.as_string()

    assert "Test Subject" in msg_str
    assert "Test Body" in msg_str
    assert "to@example.com" in msg_str


def test_build_message_with_html():
    """Verificar mensaje HTML"""
    sender = EmailSender(smtp_credentials={})

    msg = sender._build_message(
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
        subject="HTML Test",
        body="<h1>HTML Content</h1>",
        html=True
    )

    # Verificar que tiene parte HTML
    assert "text/html" in msg.as_string()


def test_build_message_with_attachment(tmp_path: Path):
    """Verificar adjunto de archivo"""
    # Crear archivo de prueba
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    sender = EmailSender(smtp_credentials={})

    msg = sender._build_message(
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
        subject="With Attachment",
        body="See attached",
        attachments=[{
            "data": test_file.read_bytes(),
            "name": "test.txt"
        }]
    )

    msg_str = msg.as_string()
    assert "test.txt" in msg_str


def test_send_with_encrypted_credentials():
    """Verificar que usa EncryptionService para credenciales"""
    from app.modules.security.encryption_service import EncryptionService

    enc_service = EncryptionService()

    # Cifrar credenciales (el EncryptionService usa diccionarios)
    encrypted_password = enc_service.encrypt({"password": "secret_password"})

    smtp_credentials = {
        "server": "smtp.example.com",
        "port": 587,
        "username": "user@example.com",
        "password_encrypted": encrypted_password
    }

    sender = EmailSender(
        smtp_credentials=smtp_credentials,
        encryption_service=enc_service
    )

    # Mock SMTP
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        sender.send(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            subject="Test",
            body="Body"
        )

        # Verificar que se descifro y uso correctamente
        mock_smtp_instance.login.assert_called_once()
        call_args = mock_smtp_instance.login.call_args

        # La password debe haberse descifrado
        assert call_args[0][1] == "secret_password"


def test_handles_smtp_error():
    """Verificar manejo de errores SMTP"""
    sender = EmailSender(smtp_credentials={
        "server": "smtp.example.com",
        "port": 587
    })

    with patch("smtplib.SMTP") as mock_smtp:
        # Simular error de autenticacion
        mock_smtp.return_value.__enter__.side_effect = Exception("Auth failed")

        with pytest.raises(Exception, match="Auth failed"):
            sender.send(
                from_addr="from@example.com",
                to_addrs=["to@example.com"],
                subject="Test",
                body="Body"
            )


def test_build_message_with_cc_and_bcc():
    """Verificar mensaje con CC y BCC"""
    sender = EmailSender(smtp_credentials={})

    msg = sender._build_message(
        from_addr="from@example.com",
        to_addrs=["to@example.com"],
        subject="Test CC/BCC",
        body="Test body",
        cc=["cc@example.com"],
        bcc=["bcc@example.com"]
    )

    msg_str = msg.as_string()
    assert "cc@example.com" in msg_str
    assert "bcc@example.com" in msg_str


def test_send_with_file_attachments(tmp_path: Path):
    """Verificar envio con adjuntos desde rutas de archivo"""
    # Crear archivos de prueba
    file1 = tmp_path / "doc1.pdf"
    file1.write_bytes(b"%PDF-1.4 fake content")

    file2 = tmp_path / "doc2.txt"
    file2.write_text("Text content")

    sender = EmailSender(smtp_credentials={
        "server": "smtp.example.com",
        "port": 587
    })

    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        result = sender.send_with_file_attachments(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            subject="Files attached",
            body="See attachments",
            file_paths=[file1, file2]
        )

        # Verificar que se envio el mensaje
        mock_smtp_instance.send_message.assert_called_once()


def test_fallback_to_plain_password():
    """Verificar fallback a password en texto plano (legacy)"""
    sender = EmailSender(smtp_credentials={
        "server": "smtp.example.com",
        "port": 587,
        "username": "user@example.com",
        "password": "plain_password"  # Legacy: sin cifrar
    })

    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        sender.send(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            subject="Test",
            body="Body"
        )

        # Verificar que uso la password en texto plano
        mock_smtp_instance.login.assert_called_once()
        call_args = mock_smtp_instance.login.call_args
        assert call_args[0][1] == "plain_password"

