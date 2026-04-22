import pytest
from server.app.database.models import ExtractionServiceConfig

class TestExtractionServiceConfigTierOverride:
    """Tests para el campo tier_override en ExtractionServiceConfig."""

    def test_tier_override_field_exists(self):
        """Verifica que el campo tier_override existe en el modelo."""
        fields = ExtractionServiceConfig.model_fields
        assert "tier_override" in fields

    def test_tier_override_default_is_none(self):
        """Verifica que el default de tier_override es None."""
        config = ExtractionServiceConfig(
            service_id="test_service",
            name="Test Service",
            system_prompt_template="Test prompt"
        )
        assert config.tier_override is None

    def test_tier_override_accepts_valid_tiers(self):
        """Verifica que acepta valores 1, 2, 3."""
        for tier in [1, 2, 3]:
            config = ExtractionServiceConfig(
                service_id=f"test_tier_{tier}",
                name=f"Test Tier {tier}",
                system_prompt_template="Test prompt",
                tier_override=tier
            )
            assert config.tier_override == tier

    def test_tier_override_coexists_with_suggested_model(self):
        """Verifica que tier_override y suggested_model pueden coexistir."""
        config = ExtractionServiceConfig(
            service_id="test_both",
            name="Test Both",
            system_prompt_template="Test prompt",
            tier_override=2,
            suggested_model="gemini-2.0-flash"
        )
        assert config.tier_override == 2
        assert config.suggested_model == "gemini-2.0-flash"

    def test_tier_override_serializes_correctly(self):
        """Verifica que tier_override se serializa correctamente a JSON."""
        config = ExtractionServiceConfig(
            service_id="test_json",
            name="Test JSON",
            system_prompt_template="Test prompt",
            tier_override=3
        )
        data = config.model_dump()
        assert data["tier_override"] == 3
