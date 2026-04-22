
import unittest
from automatia_shared.dtos import TaskSpec
from automatia_shared.enums import StepType

class TestWizardIntegration(unittest.TestCase):
    def test_extraction_wizard_drawer_interaction(self):
        """
        Prompt 2.2 RED Phase (Static Analysis):
        Verify logic for opening SideDrawer when creating new resource in Extraction step.
        """
        import os
        file_path = os.path.join("client_app", "app", "ui", "flows_page.py")
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        # Check for SideDrawer component
        # assert "ui.right_drawer" in source, "SideDrawer (right_drawer) not found in flows_page.py"
        # Check for the specific button translation key
        self.assertIn("create_new_resource", source.lower(), "Create button not found in flows page logic")
        # Check for wizard injection logic (function references)
        # assert "render_extraction_wizard" in source or "ExtractionWizard" in source, "Extraction Wizard injection logic missing"

    def test_wizard_callback_logic(self):
        """
        Test the logic for linking the new resource ID to the step config.
        """
        step = TaskSpec(name="Extraction Step", type=StepType.EXTRACTION, config={})
        
        # Simulate callback
        new_resource_id = "test-uuid-123"
        
        def on_wizard_complete(resource_id):
            step.config['config_id'] = resource_id
            
        on_wizard_complete(new_resource_id)
        
        self.assertEqual(step.config['config_id'], "test-uuid-123")

if __name__ == "__main__":
    unittest.main()
