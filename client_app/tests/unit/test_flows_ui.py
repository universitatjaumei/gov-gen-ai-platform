
import pytest

def test_ai_flow_assistant_ui_components_existence():
    """
    Fase RED Checklist (Static Analysis):
    1. Verify existence of valid 'ai_assistant_title' translation key usage.
    2. Verify existence of 'generate_proposal' button logic.
    """
    import os
    # Read file content directly to avoid Import overhead/errors in this environment
    file_path = os.path.join("client_app", "app", "ui", "flows_page.py")
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    # Assertions
    assert "ai_assistant_title" in source, "AI Assistant Title translation key missing in flows_page.py"
    assert "generate_proposal" in source, "Generate Proposal translation key missing in flows_page.py"
    assert "orchestrate_flow" in source, "Brain Orchestrator method call missing in flows_page.py"

@pytest.mark.asyncio
async def test_ai_assistant_integration_logic():
    """
    Fase RED: Verify logic for Brain Client integration.
    """
    import os
    file_path = os.path.join("client_app", "app", "ui", "flows_page.py")
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    assert "BrainAPIClient" in source, "BrainAPIClient not used in flows_page.py"
    assert "AnonymizationContext" in source, "AnonymizationContext not used in flows_page.py"
