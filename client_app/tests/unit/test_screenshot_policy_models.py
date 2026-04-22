
import pytest
from sqlmodel import Session, create_engine, SQLModel
from client_app.app.database.models import SecurityPolicy
from automatia_shared.enums import ScreenshotPolicyEnum


@pytest.fixture
def memory_db():
    """Base de datos en memoria para tests."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


class TestScreenshotPolicyEnum:
    """Tests para el enum de políticas de captura."""

    def test_enum_has_three_values(self):
        """El enum debe tener exactamente 3 valores."""
        assert len(ScreenshotPolicyEnum) == 3

    def test_enum_values_are_strings(self):
        """Los valores deben ser strings serializables."""
        assert ScreenshotPolicyEnum.BLOCK.value == "BLOCK"
        assert ScreenshotPolicyEnum.REVIEW.value == "REVIEW"
        assert ScreenshotPolicyEnum.TRUSTED.value == "TRUSTED"

    def test_enum_is_string_subclass(self):
        """El enum debe heredar de str para serialización JSON."""
        assert isinstance(ScreenshotPolicyEnum.BLOCK, str)


class TestSecurityPolicyScreenshotFields:
    """Tests para los nuevos campos en SecurityPolicy."""

    def test_default_screenshot_policy_is_review(self, memory_db):
        """Por defecto, la política debe ser REVIEW (la más segura usable)."""
        with Session(memory_db) as session:
            policy = SecurityPolicy(name="test_policy")
            session.add(policy)
            session.commit()
            session.refresh(policy)

            assert policy.screenshot_policy == ScreenshotPolicyEnum.REVIEW.value

    def test_can_set_screenshot_policy_block(self, memory_db):
        """Debe poder configurarse como BLOCK."""
        with Session(memory_db) as session:
            policy = SecurityPolicy(
                name="strict_policy",
                screenshot_policy=ScreenshotPolicyEnum.BLOCK.value
            )
            session.add(policy)
            session.commit()
            session.refresh(policy)

            assert policy.screenshot_policy == ScreenshotPolicyEnum.BLOCK.value

    def test_trusted_domains_defaults_to_empty_list(self, memory_db):
        """La lista de dominios trusted debe estar vacía por defecto."""
        with Session(memory_db) as session:
            policy = SecurityPolicy(name="test_policy")
            session.add(policy)
            session.commit()
            session.refresh(policy)

            import json
            domains = json.loads(policy.trusted_screenshot_domains)
            assert domains == []

    def test_can_store_trusted_domains_as_json(self, memory_db):
        """Debe poder almacenar lista de dominios como JSON."""
        import json
        domains = ["boe.es", "sede.agenciatributaria.gob.es"]

        with Session(memory_db) as session:
            policy = SecurityPolicy(
                name="partial_trust",
                screenshot_policy=ScreenshotPolicyEnum.TRUSTED.value,
                trusted_screenshot_domains=json.dumps(domains)
            )
            session.add(policy)
            session.commit()
            session.refresh(policy)

            loaded = json.loads(policy.trusted_screenshot_domains)
            assert loaded == domains

    def test_policy_persists_across_sessions(self, memory_db):
        """Los valores deben persistir correctamente."""
        import json

        with Session(memory_db) as session:
            policy = SecurityPolicy(
                name="persistent_test",
                screenshot_policy=ScreenshotPolicyEnum.BLOCK.value,
                trusted_screenshot_domains=json.dumps(["example.com"])
            )
            session.add(policy)
            session.commit()
            policy_id = policy.id

        # Nueva sesión
        with Session(memory_db) as session:
            loaded = session.get(SecurityPolicy, policy_id)
            assert loaded.screenshot_policy == ScreenshotPolicyEnum.BLOCK.value
            assert "example.com" in loaded.trusted_screenshot_domains
