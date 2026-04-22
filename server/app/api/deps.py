
from typing import AsyncGenerator, Optional, Union
from fastapi import Header, HTTPException, Depends, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.db import server_engine
from server.app.database.models import AdminAccount, PartnerAccount
from server.app.core.config import IS_DEV_MODE

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining a database session."""
    async with AsyncSession(server_engine) as session:
        yield session

async def get_current_active_user(
    x_role_context: str = Header(..., alias="X-Role-Context"),
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_session)
) -> Union[AdminAccount, PartnerAccount]:
    """
    Resuelve el usuario activo basado en la cabecera de contexto de rol.
    
    X-Role-Context: 'admin' | 'partner'
    Authorization: 'Bearer <identity>' (En esta fase, identity es el email para pruebas)
    """
    # Validar formato Bearer
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use Bearer <email>"
        )
    
    identity = authorization.replace("Bearer ", "").strip()
    
    if x_role_context == "admin":
        statement = select(AdminAccount).where(AdminAccount.email == identity)
        result = await session.exec(statement)
        user = result.first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account not found or inactive"
            )
        return user
        
    elif x_role_context == "partner":
        statement = select(PartnerAccount).where(PartnerAccount.email == identity)
        result = await session.exec(statement)
        user = result.first()
        if not user:
            if IS_DEV_MODE:
                # Auto-provisioning in DEV mode
                user = PartnerAccount(
                    partner_id="p_dev_auto",
                    email=identity,
                    name="Dev Partner",
                    is_active=True
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Partner account not found"
                )
        
        if not user.is_active:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Partner account inactive"
            )
            
        return user
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-Role-Context: {x_role_context}"
        )
