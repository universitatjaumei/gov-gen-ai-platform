"""Registry de perfiles de informe — 9R.2.1.

Análogo a GraphProfileRegistry del bloque 9B. Cada perfil encapsula la spec
por defecto, los pipelines aplicables y las políticas de revisión e IA.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
)

# Alias — la definición formal del tipo pipeline llega en 9R.5.1
ExtractionPipelineId = str


@runtime_checkable
class ReportProfile(Protocol):
    @property
    def profile_id(self) -> str: ...
    def default_spec(self) -> ReportTemplateSpec: ...
    def applicable_pipelines(self) -> list[ExtractionPipelineId]: ...
    def review_policy(self) -> ReviewPolicy: ...
    def ai_block_policy(self) -> AIBlockPolicy: ...


class ReportProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, ReportProfile] = {}

    def register(self, profile: ReportProfile) -> None:
        pid = profile.profile_id
        if pid in self._profiles:
            raise ValueError(f"Profile {pid!r} already registered")
        self._profiles[pid] = profile

    def get(self, profile_id: str) -> ReportProfile:
        if profile_id not in self._profiles:
            raise KeyError(f"Unknown report profile: {profile_id!r}")
        return self._profiles[profile_id]

    def list(self) -> list[str]:
        return list(self._profiles.keys())


# Instancia global — accesible via `from server.app.modules.redaccion.profiles import registry`
registry = ReportProfileRegistry()
