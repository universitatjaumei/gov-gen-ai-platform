"""
Servicio Knowledge Orchestrator - Lado del Cliente (Refactorizado)
Recopilador de inventario local para el Brain Server.

Este servicio se encarga exclusivamente de leer los recursos locales 
del cliente para enviarlos al servidor como contexto en las peticiones de IA.
"""

from typing import List, Dict, Any
from pathlib import Path
import json


class KnowledgeOrchestratorService:
    """
    Servicio ligero encargado de gestionar y exponer el inventario de recursos locales
    (scripts, automatizaciones, contratos UI) al ecosistema global.
    """
    
    _instance = None

    def __new__(cls):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_local_inventory(self) -> List[Dict[str, Any]]:
        """
        Escanea y obtiene los recursos disponibles en la biblioteca local del cliente.
        Lee los scripts Python (.py), busca metadatos asociados (.json) y
        archivos de documentación (.md) para construir un catálogo descriptivo.

        Returns:
            Lista de diccionarios, cada uno representando un recurso con su ID,
            nombre, descripción y contrato de interfaz (ui_contract).
        """
        items = []

        # Directorios estándar de almacenamiento local
        scripts_dir = Path("data/storage/scripts/src")
        docs_dir = Path("data/storage/scripts/docs")

        if not scripts_dir.exists():
            return items

        # Buscar scripts .py
        for script_file in scripts_dir.glob("*.py"):
            script_id = script_file.stem
            
            # Intentar cargar metadata (ui_contract)
            # En esta arquitectura simplificada, podemos buscar un .json de metadata
            # o asumir valores por defecto si no existe.
            ui_contract = {}
            metadata_file = scripts_dir / f"{script_id}.json"
            if metadata_file.exists():
                try:
                    ui_contract = json.loads(metadata_file.read_text(encoding='utf-8')).get('ui_contract', {})
                except:
                    pass

            # Intentar cargar documentación (.md)
            description = ""
            doc_file = docs_dir / f"{script_id}.md"
            if doc_file.exists():
                try:
                    # Usar la primera línea como descripción corta
                    lines = doc_file.read_text(encoding='utf-8').splitlines()
                    description = lines[0].strip('# ') if lines else ""
                except:
                    pass

            items.append({
                "id": script_id,
                "name": script_id.replace("_", " ").title(),
                "description": description or f"Script local: {script_id}",
                "ui_contract": ui_contract
            })

        return items


# Singleton instance
knowledge_orchestrator = KnowledgeOrchestratorService()
