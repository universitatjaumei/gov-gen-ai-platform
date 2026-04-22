import pytest
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'shared'))

from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def test_add_atom_updates_flow_steps():
    """Test that adding an atom creates a new TaskSpec in the flow."""
    # Arrange
    flow = FlowSpec(name="Test Flow", steps=[])
    
    # Act
    new_step = TaskSpec(
        name="Extractor PDF",
        type=StepType.EXTRACTION,
        config={}
    )
    flow.steps.append(new_step)
    
    # Assert
    assert len(flow.steps) == 1
    assert flow.steps[0].name == "Extractor PDF"
    assert flow.steps[0].type == StepType.EXTRACTION

def test_flow_spec_serialization():
    """Test that FlowSpec can be serialized to/from dict."""
    # Arrange
    flow = FlowSpec(
        name="Test Flow",
        steps=[
            TaskSpec(name="Step 1", type=StepType.EXTRACTION, config={}),
            TaskSpec(name="Step 2", type=StepType.ETL, config={})
        ]
    )
    
    # Act
    flow_dict = flow.model_dump()
    restored_flow = FlowSpec(**flow_dict)
    
    # Assert
    assert restored_flow.name == "Test Flow"
    assert len(restored_flow.steps) == 2
    assert restored_flow.steps[0].type == StepType.EXTRACTION
    assert restored_flow.steps[1].type == StepType.ETL
