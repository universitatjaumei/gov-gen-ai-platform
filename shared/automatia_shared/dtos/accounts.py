
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AdminProfileDTO(BaseModel):
    """Perfil de Administrador del Sistema."""
    admin_id: int
    name: str
    email: str
    is_active: bool = True
    created_at: datetime

class PartnerProfileDTO(BaseModel):
    """Perfil de Partner."""
    partner_id: str
    name: str
    email: str
    credits_balance: int = 0
    is_active: bool = True
    created_at: datetime

class ClientProfileDTO(BaseModel):
    """Perfil de Cliente."""
    client_id: str
    name: str
    partner_id: str
    is_active: bool = True
    created_at: datetime
