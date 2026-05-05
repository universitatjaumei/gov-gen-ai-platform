"""Registry de perfiles de grafo público.

Deploy: edge
"""
from collections.abc import Callable
from typing import Any

from server.app.modules.agents_hub.agent.public_graphs.types import PublicGraphProfile


class UnknownProfileError(KeyError):
    pass


ProfileFactory = Callable[..., Any]


class GraphProfileRegistry:
    """Catálogo de perfiles de grafo público registrados en tiempo de ejecución."""

    def __init__(self) -> None:
        self._registry: dict[str, ProfileFactory] = {}

    def register_profile(self, profile: PublicGraphProfile, factory: ProfileFactory) -> None:
        self._registry[profile.value] = factory

    def get_profile(self, profile_name: str) -> ProfileFactory:
        try:
            return self._registry[profile_name]
        except KeyError:
            raise UnknownProfileError(profile_name)

    def list_profiles(self) -> list[str]:
        return list(self._registry.keys())


_default_registry = GraphProfileRegistry()


def register_profile(profile: PublicGraphProfile, factory: ProfileFactory) -> None:
    _default_registry.register_profile(profile, factory)


def get_profile(profile_name: str) -> ProfileFactory:
    return _default_registry.get_profile(profile_name)


def list_profiles() -> list[str]:
    return _default_registry.list_profiles()
