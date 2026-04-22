import pytest
import asyncio
from unittest.mock import MagicMock, patch
from client_app.app.ui.components.script_creation_wizard import WizardState, ScriptCreationWizard
from client_app.app.database.models import WizardDraft
from client_app.app.database.db import client_engine, init_client_db
from sqlmodel import select, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

@pytest.fixture(autouse=True)
async def setup_db():
    # Force creation of tables including new WizardDraft
    async with client_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_wizard_state_to_dict_serialization():
    state = WizardState()
    state.user_prompt = "Generate a script to read CSV"
    state.phase = "generation"
    
    data = state.to_dict()
    assert data['user_prompt'] == "Generate a script to read CSV"
    assert data['phase'] == "generation"

@pytest.mark.asyncio
async def test_wizard_state_from_dict_restoration():
    state = WizardState()
    data = {
        "user_prompt": "Restored prompt",
        "phase": "testing",
        "output_type": "dataframe"
    }
    state.from_dict(data)
    assert state.user_prompt == "Restored prompt"
    assert state.phase == "testing"
    assert state.output_type == "dataframe"

@pytest.mark.asyncio
async def test_wizard_save_draft_persists_to_db():
    # Mock NiceGUI to avoid "slot stack empty" error
    with patch('nicegui.ui.column'), patch('nicegui.ui.timer'):
        wizard = ScriptCreationWizard()
        wizard.state.user_prompt = "Persistence test prompt"
        wizard.state.phase = "description"
        
        await wizard.save_draft()
        
        async with AsyncSession(client_engine) as session:
            result = await session.execute(select(WizardDraft).where(WizardDraft.wizard_type == "custom_script"))
            draft = result.scalar_one_or_none()
            assert draft is not None
            assert draft.data['user_prompt'] == "Persistence test prompt"

@pytest.mark.asyncio
async def test_wizard_clear_draft_removes_from_db():
    with patch('nicegui.ui.column'), patch('nicegui.ui.timer'):
        wizard = ScriptCreationWizard()
        wizard.state.user_prompt = "Cleanup test prompt"
        await wizard.save_draft()
        
        async with AsyncSession(client_engine) as session:
            result = await session.execute(select(WizardDraft).where(WizardDraft.wizard_type == "custom_script"))
            assert result.scalar_one_or_none() is not None
            
        await wizard.clear_draft()
        
        async with AsyncSession(client_engine) as session:
            result = await session.execute(select(WizardDraft).where(WizardDraft.wizard_type == "custom_script"))
            assert result.scalar_one_or_none() is None
