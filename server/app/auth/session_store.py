
"""
STUB: SessionStore para P23B.
La implementacion real vendra en P27.
"""
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, Dict

class SessionStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate(self, email: str, password: str) -> Optional[Dict[str, str]]:
        """
        Stub de autenticacion.
        En P23B usamos from_dev_mode, asi que esto es solo para que la UI no rompa.
        Para pruebas, aceptamos cualquier email que empiece por 'active' con password 'test'.
        """
        if password == "test":
             return {"token": "dummy_token_p23b", "partner_id": "partner_dev"}
        return None

    async def validate_session(self, token: str):
        return None
