"""Tipos compartidos de la librería de grafos públicos."""
from enum import Enum


class PublicGraphProfile(str, Enum):
    PUBLIC_KB_RICH = "PUBLIC_KB_RICH"
    PUBLIC_PORTAL_ROUTER = "PUBLIC_PORTAL_ROUTER"
    PUBLIC_PORTAL_AGGREGATOR = "PUBLIC_PORTAL_AGGREGATOR"
