"""Tests del registry de perfiles de grafo público — TDD RED (9B.1)."""
import pytest

from server.app.modules.agents_hub.agent.public_graphs.types import PublicGraphProfile
from server.app.modules.agents_hub.agent.public_graphs.registry import (
    GraphProfileRegistry,
    UnknownProfileError,
)


def _make_factory(name: str):
    def factory():
        return f"graph:{name}"
    return factory


class TestGraphProfileRegistry:

    def setup_method(self):
        self.registry = GraphProfileRegistry()

    def test_registry_lists_profiles(self) -> None:
        self.registry.register_profile(PublicGraphProfile.PUBLIC_KB_RICH, _make_factory("kb_rich"))
        self.registry.register_profile(PublicGraphProfile.PUBLIC_PORTAL_AGGREGATOR, _make_factory("aggregator"))

        profiles = self.registry.list_profiles()

        assert PublicGraphProfile.PUBLIC_KB_RICH.value in profiles
        assert PublicGraphProfile.PUBLIC_PORTAL_AGGREGATOR.value in profiles

    def test_registry_raises_on_unknown_profile(self) -> None:
        with pytest.raises(UnknownProfileError, match="unknown_profile"):
            self.registry.get_profile("unknown_profile")

    def test_registry_can_register_and_get_profile(self) -> None:
        factory = _make_factory("kb_rich")
        self.registry.register_profile(PublicGraphProfile.PUBLIC_KB_RICH, factory)

        retrieved = self.registry.get_profile(PublicGraphProfile.PUBLIC_KB_RICH.value)

        assert retrieved is factory

    def test_registry_lists_empty_when_no_profiles_registered(self) -> None:
        assert self.registry.list_profiles() == []

    def test_registry_overwrites_on_duplicate_registration(self) -> None:
        factory_a = _make_factory("a")
        factory_b = _make_factory("b")
        self.registry.register_profile(PublicGraphProfile.PUBLIC_KB_RICH, factory_a)
        self.registry.register_profile(PublicGraphProfile.PUBLIC_KB_RICH, factory_b)

        assert self.registry.get_profile(PublicGraphProfile.PUBLIC_KB_RICH.value) is factory_b
