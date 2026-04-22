
import unittest
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def move_step_logic(flow: FlowSpec, index: int, direction: int):
    """
    Logic standalone for moving steps.
    Direction: -1 (up), 1 (down)
    """
    new_index = index + direction
    if 0 <= new_index < len(flow.steps):
        flow.steps[index], flow.steps[new_index] = flow.steps[new_index], flow.steps[index]
        return True
    return False

class TestFlowLogic(unittest.TestCase):
    def test_reorder_steps_logic(self):
        """
        Test logic for reordering steps in a FlowSpec.
        """
        # Setup
        steps = [
            TaskSpec(name="Step 1", type=StepType.EXTRACTION, config={}),
            TaskSpec(name="Step 2", type=StepType.ETL, config={}),
            TaskSpec(name="Step 3", type=StepType.EMAIL, config={})
        ]
        flow = FlowSpec(name="Test Flow", steps=steps)

        # 1. Move Step 2 (index 1) UP to index 0
        success = move_step_logic(flow, 1, -1)
        self.assertTrue(success)
        self.assertEqual(flow.steps[0].name, "Step 2")
        self.assertEqual(flow.steps[1].name, "Step 1")
        self.assertEqual(flow.steps[2].name, "Step 3")

        # 2. Move Step 2 (now at index 0) UP again (Boundary Check)
        success = move_step_logic(flow, 0, -1)
        self.assertFalse(success) # Should not move
        self.assertEqual(flow.steps[0].name, "Step 2")

        # 3. Move Step 3 (index 2) DOWN (Boundary Check)
        success = move_step_logic(flow, 2, 1)
        self.assertFalse(success) # Should not move
        self.assertEqual(flow.steps[2].name, "Step 3")

        # 4. Move Step 1 (now at index 1) DOWN to index 2
        success = move_step_logic(flow, 1, 1)
        self.assertTrue(success)
        self.assertEqual(flow.steps[1].name, "Step 3")
        self.assertEqual(flow.steps[2].name, "Step 1")

if __name__ == "__main__":
    unittest.main()
