
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from server.app.api.deps import get_current_active_user
from server.app.database.models import PartnerAccount

@pytest.mark.asyncio
async def test_get_current_user_injects_partner_id():
    """
    Verifica que get_current_active_user auto-aprovisiona un partner en modo DEV
    si no existe, y retorna el usuario con partner_id inyectado.
    """
    # 1. Setup mocks
    mock_session = AsyncMock()
    
    # Mockear el resultado de la consulta DB: inicialmente None (usuario no existe)
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec.return_value = mock_result
    
    # Mockear el add/commit/refresh para la creación de usuario
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    # 2. Definir inputs
    x_role_context = "partner"
    authorization = "Bearer dev@test.com"
    
    # 3. Importar IS_DEV_MODE y parchearlo a True para este test
    with patch("server.app.api.deps.IS_DEV_MODE", True):
        # Ejecutar la función bajo prueba
        user = await get_current_active_user(
            x_role_context=x_role_context,
            authorization=authorization,
            session=mock_session
        )
        
        # 4. Verificaciones
        # a) Se debió intentar crear el usuario
        mock_session.add.assert_called_once()
        created_user = mock_session.add.call_args[0][0]
        assert isinstance(created_user, PartnerAccount)
        assert created_user.email == "dev@test.com"
        assert created_user.name == "Dev Partner"
        assert created_user.partner_id is not None
        
        # b) Se debió hacer commit y refresh
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(created_user)
        
        # c) El usuario retornado debe ser el creado (o lo que refresh actualice)
        assert user == created_user
        
        # d) Verificar que podemos acceder a partner_id (en un objeto real esto es auto-generado,
        # aquí verificamos que el objeto retornado es del tipo correcto)
        assert hasattr(user, "partner_id")

@pytest.mark.asyncio
async def test_get_current_user_fails_if_not_dev_and_no_user():
    """
    Verifica que si NO estamos en modo DEV, y el usuario no existe, se lanza 403.
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec.return_value = mock_result
    
    with patch("server.app.api.deps.IS_DEV_MODE", False):
        with pytest.raises(HTTPException) as excinfo:
            await get_current_active_user(
                x_role_context="partner",
                authorization="Bearer prod@test.com",
                session=mock_session
            )
        assert excinfo.value.status_code == 403
