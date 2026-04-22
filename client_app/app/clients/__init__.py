"""
Clientes para comunicación con el servidor Brain.

Este módulo contiene:
- BrainAPIClient: Cliente HTTP único para modo split y monolito.
  En modo monolito, se comunica via localhost a través del router de la API
  para garantizar la consistencia del código y facilitar el mantenimiento.
"""

from client_app.app.clients.brain_client import BrainAPIClient

__all__ = ["BrainAPIClient"]
