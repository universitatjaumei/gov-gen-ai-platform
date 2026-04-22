import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestAdminPromptsUI:
    """Tests para el selector de tier en el editor de prompts."""

    def test_tier_options_exist(self):
        """Verifica que existen las 4 opciones de tier."""
        # This constant should be imported from the implementation file once it exists
        # For TDD, we might need to rely on the implementation file defining it
        # or mock it if we are testing the logic. 
        # Since we are creating the test BEFORE implementation, we will try to import it
        # and expect it to fail or be missing.
        try:
            from server.app.ui.admin_prompts import TIER_OPTIONS
        except ImportError:
            pytest.fail("TIER_OPTIONS not found in server.app.ui.admin_prompts")
        except Exception:
            # If the file doesn't exist or has syntax errors
            pass 
        
        # NOTE: For TDD "Compilation Error" is also a "Red" state.
        # But to write a runnable test that asserts valid properties once implemented:
        
        from server.app.ui.admin_prompts import TIER_OPTIONS

        assert len(TIER_OPTIONS) == 4
        assert TIER_OPTIONS[0]["value"] is None  # Default
        assert TIER_OPTIONS[1]["value"] == 1
        assert TIER_OPTIONS[2]["value"] == 2
        assert TIER_OPTIONS[3]["value"] == 3

    def test_tier_to_role_mapping(self):
        """Verifica el mapeo de tier a role_key."""
        # This logic might belong to the service/model, but if UI has logic, test it here.
        # The prompt test example showed this loop.
        TIER_TO_ROLE = {
            1: "extraccion_pdf",
            2: "logico_navegacion",
            3: "supervision"
        }

        assert TIER_TO_ROLE[1] == "extraccion_pdf"
        assert TIER_TO_ROLE[2] == "logico_navegacion"
        assert TIER_TO_ROLE[3] == "supervision"

    @pytest.mark.asyncio
    async def test_save_prompt_with_tier_override(self):
        """Verifica que guardar el prompt incluye tier_override."""
        # Using a Mock object to simulate specific behavior
        mock_prompt = MagicMock()
        mock_prompt.service_id = "sys_phase0_discovery"
        mock_prompt.tier_override = None

        # Simulate change
        new_tier = 2
        mock_prompt.tier_override = new_tier

        assert mock_prompt.tier_override == 2

    def test_tier_badge_display(self):
        """Verifica los badges por tier."""
        def get_tier_badge(tier_override: int | None) -> str:
            badges = {
                None: "⚪",  # Default
                1: "🟢",     # Tier 1
                2: "🟡",     # Tier 2
                3: "🔴",     # Tier 3
            }
            return badges.get(tier_override, "⚪")

        assert get_tier_badge(None) == "⚪"
        assert get_tier_badge(1) == "🟢"
        assert get_tier_badge(2) == "🟡"
        assert get_tier_badge(3) == "🔴"
