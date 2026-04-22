import pytest
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'shared'))

from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType
from client_app.app.services.flow_diagram_generator import flow_diagram_generator

def test_generate_mermaid_empty_flow():
    """Test Mermaid generation for empty flow."""
    flow = FlowSpec(name="Empty Flow", steps=[])
    mermaid_code = flow_diagram_generator.generate(flow)
    
    assert "graph" in mermaid_code.lower()
    assert "Start([Inicio])" in mermaid_code
    assert "End([Fin])" in mermaid_code

def test_generate_mermaid_with_steps():
    """Test Mermaid generation includes all steps."""
    flow = FlowSpec(
        name="Test Flow",
        steps=[
            TaskSpec(name="Extract PDF", type=StepType.EXTRACTION, config={}),
            TaskSpec(name="Transform Data", type=StepType.ETL, config={})
        ]
    )
    
    mermaid_code = flow_diagram_generator.generate(flow)
    
    # Verify all steps are present in some form
    assert "Extract PDF" in mermaid_code
    assert "Transform Data" in mermaid_code
    
    # Verify connections
    assert "Start --> S1" in mermaid_code
    assert "S1 --> S2" in mermaid_code
    assert "S2 --> End([Fin])" in mermaid_code

def test_add_step_updates_mermaid():
    """Test that adding a step generates updated Mermaid code."""
    # Initial flow
    flow = FlowSpec(name="Dynamic Flow", steps=[
        TaskSpec(name="Step 1", type=StepType.EXTRACTION, config={})
    ])
    
    initial_mermaid = flow_diagram_generator.generate(flow)
    
    # Add new step
    new_step = TaskSpec(name="Step 2", type=StepType.ETL, config={})
    flow.steps.append(new_step)
    
    updated_mermaid = flow_diagram_generator.generate(flow)
    
    # Verify update
    assert "Step 1" in initial_mermaid
    assert "Step 2" not in initial_mermaid
    assert "Step 2" in updated_mermaid
    assert initial_mermaid != updated_mermaid
