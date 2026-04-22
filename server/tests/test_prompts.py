
import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import ExtractionServiceConfig
from server.app.database.seeds_prompts import seed_system_prompts

@pytest.mark.asyncio
async def test_sys_flow_orchestrator_registration():
    """
    Test RED-GREEN-REFACTOR for sys_flow_orchestrator registration.
    
    1. Executes the seeding process.
    2. Verifies if 'sys_flow_orchestrator' is present in the database.
    """
    
    # 1. Execute Seed
    await seed_system_prompts()
    
    # 2. Verify existence
    async with AsyncSession(server_engine) as session:
        statement = select(ExtractionServiceConfig).where(
            ExtractionServiceConfig.service_id == "sys_flow_orchestrator"
        )
        result = await session.exec(statement)
        service = result.first()
        
        # Assertion (Should FAIL in RED phase, PASS in GREEN phase)
        assert service is not None, "sys_flow_orchestrator should be registered in the database"
        
        # Additional validations for GREEN phase
        if service:
            assert service.name == "System: Flow Orchestrator"
            assert service.tier_override == 3
            # Check for specific Blueprint/Orchestrator logic keywords in the prompt to ensure it's the right one
            assert "TaskSpec" in service.system_prompt_template
            assert "StepType" in service.system_prompt_template
