"""Profiles package — auto-registra GENERIC_REPORT al importarse."""
from server.app.modules.redaccion.profiles.registry import registry
from server.app.modules.redaccion.profiles.generic_report import GenericReportProfile

registry.register(GenericReportProfile())

__all__ = ["registry"]
