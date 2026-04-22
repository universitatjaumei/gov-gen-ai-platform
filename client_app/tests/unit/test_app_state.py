
import pytest
from datetime import datetime
from client_app.app.core.state import AppState
from automatia_shared.dtos import AdminProfileDTO, PartnerProfileDTO, ClientProfileDTO

def test_initial_state_user_is_none():
    """AppState should start with no user."""
    state = AppState()
    assert state.current_user is None
    assert state.current_role is None

def test_set_role_admin_creates_profile():
    """Setting role to admin should create/mock an admin profile."""
    state = AppState()
    state.set_role("admin")
    
    assert state.current_role == "admin"
    assert isinstance(state.current_user, AdminProfileDTO)
    assert state.current_user.name == "Super Admin"
    assert state.current_user.email == "admin@automatia.com"

def test_set_role_partner_creates_profile():
    """Setting role to partner should create/mock a partner profile."""
    state = AppState()
    state.set_role("partner")
    
    assert state.current_role == "partner"
    assert isinstance(state.current_user, PartnerProfileDTO)
    assert state.current_user.partner_id == "part_001"
    assert state.current_user.credits_balance == 1000

def test_set_role_client_creates_profile():
    """Setting role to client should create/mock a client profile."""
    state = AppState()
    state.set_role("client")
    
    assert state.current_role == "client"
    assert isinstance(state.current_user, ClientProfileDTO)
    assert state.current_user.client_id == "cli_001"

def test_switching_roles_updates_profile():
    """Switching roles should update both role and current_user."""
    state = AppState()
    state.set_role("admin")
    assert isinstance(state.current_user, AdminProfileDTO)
    
    state.set_role("partner")
    assert isinstance(state.current_user, PartnerProfileDTO)
    assert state.current_role == "partner"

def test_clear_role_cleans_profile():
    """Setting role to None or empty should clear the profile."""
    state = AppState()
    state.set_role("admin")
    assert state.current_user is not None
    
    state.set_role(None)
    assert state.current_user is None
    assert state.current_role is None

def test_unknown_role_raises_value_error():
    """Setting an unknown role should raise ValueError."""
    state = AppState()
    with pytest.raises(ValueError, match="Unknown role"):
        state.set_role("hacker")
