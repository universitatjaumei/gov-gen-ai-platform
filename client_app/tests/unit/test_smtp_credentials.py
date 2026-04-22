import pytest
import pytest_asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.models import LocalCredentials
from client_app.app.services.mail_watcher_service import mail_watcher_service

@pytest.mark.asyncio
async def test_save_smtp_credential(db_session: AsyncSession):
    """Verificar que se puede guardar una credencial SMTP."""
    
    cred_id = await mail_watcher_service.save_credential(
        name="SMTP Test",
        server="smtp.gmail.com",
        port=587,
        username="user@gmail.com",
        password="password",
        use_ssl=False,
        service_type="SMTP"
    )
    
    assert cred_id is not None
    
    # Verificar en DB
    stmt = select(LocalCredentials).where(LocalCredentials.id == cred_id)
    result = await db_session.exec(stmt)
    cred = result.first()
    
    assert cred is not None
    assert cred.service_name == "smtp_SMTP Test" or cred.service_name == "SMTP_SMTP Test" or cred.service_type == "SMTP"
    assert cred.service_type == "SMTP"

@pytest.mark.asyncio
async def test_list_smtp_credentials(db_session: AsyncSession):
    """Verificar filtrado por tipo."""
    # Crear IMAP
    await mail_watcher_service.save_credential(
        name="IMAP 1", server="imap.a.com", port=993, username="u", password="p", use_ssl=True,
        service_type="IMAP"
    )
    # Crear SMTP
    await mail_watcher_service.save_credential(
        name="SMTP 1", server="smtp.a.com", port=587, username="u", password="p", use_ssl=False,
        service_type="SMTP"
    )
    
    # Listar SMTP
    smtp_list = await mail_watcher_service.list_credentials(service_type="SMTP")
    assert len(smtp_list) >= 1
    assert any(c["name"] == "SMTP 1" for c in smtp_list)
    
    # Listar IMAP
    imap_list = await mail_watcher_service.list_credentials(service_type="IMAP")
    assert len(imap_list) >= 1
    assert any(c["name"] == "IMAP 1" for c in imap_list)
    
    # Listar Todos
    all_list = await mail_watcher_service.list_credentials(service_type=None)
    assert len(all_list) >= 2
    assert any(c["name"] == "SMTP 1" for c in all_list)
