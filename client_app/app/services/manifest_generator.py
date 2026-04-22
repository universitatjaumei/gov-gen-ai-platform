"""
Generador de manifiesto para paquetes de automatismos.
Prompt 1.4 del sistema de exportación/importación de automatismos.

El manifiesto es el corazón del paquete .automatia:
- Contiene metadatos del paquete (nombre, descripción, fecha)
- Registra información de origen (licencia, cliente, partner)
- Lista todos los archivos incluidos con sus hashes SHA256
- La firma se aplica al manifiesto completo
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Optional


class ManifestGenerator:
    """
    Generador de manifiestos para paquetes de automatismos.

    El manifiesto tiene la siguiente estructura:
    {
        "version": "1.0",
        "name": "<nombre del paquete>",
        "description": "<descripción opcional>",
        "export_date": "<ISO timestamp>Z",
        "source": {
            "license_id": "<ID de licencia>",
            "client_id": "<ID de cliente>",
            "partner_id": "<ID de partner>",
            "machine_id": "<ID de máquina opcional>"
        },
        "contents": {
            "scripts": ["script1.py", "script2.py"],
            "playbooks": ["playbook1.json"],
            "workflows": ["flow1.json"]
        },
        "file_hashes": {
            "<ruta/archivo>": "<SHA256 hash>",
            ...
        },
        "signature": null,  // Se llena después con add_signature()
        "package_hash": null  // Se llena después con add_signature()
    }
    """

    def _get_export_date(self) -> str:
        """
        Obtiene fecha de exportación en formato ISO con Z.

        Método separado para facilitar testing con mocks.

        Returns:
            str: Timestamp ISO con sufijo Z (UTC)
        """
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def generate(
        self,
        package_name: str,
        source_info: Dict[str, str],
        files: Dict[str, bytes],
        description: Optional[str] = None
    ) -> str:
        """
        Genera manifest.json para el paquete.

        Args:
            package_name: Nombre descriptivo del paquete
            source_info: Información de origen con claves:
                - license_id: ID de licencia (requerido)
                - client_id: ID de cliente (requerido)
                - partner_id: ID de partner (requerido)
                - machine_id: ID de máquina (opcional)
            files: Diccionario de archivos {ruta_relativa: contenido_bytes}
            description: Descripción opcional del paquete

        Returns:
            str: JSON del manifiesto (formateado con indentación)
        """
        # Calcular hashes de todos los archivos
        file_hashes = {}
        for filepath, content in files.items():
            file_hashes[filepath] = hashlib.sha256(content).hexdigest()

        # Clasificar contenido por tipo
        scripts = [
            f.replace("scripts/", "")
            for f in files.keys()
            if f.startswith("scripts/")
        ]
        playbooks = [
            f.replace("playbooks/", "")
            for f in files.keys()
            if f.startswith("playbooks/")
        ]
        workflows = [
            f.replace("workflows/", "")
            for f in files.keys()
            if f.startswith("workflows/")
        ]

        # Construir estructura del manifiesto
        manifest = {
            "version": "1.0",
            "name": package_name,
            "description": description,
            "export_date": self._get_export_date(),
            "source": {
                "license_id": source_info.get("license_id"),
                "client_id": source_info.get("client_id"),
                "partner_id": source_info.get("partner_id"),
                "machine_id": source_info.get("machine_id")
            },
            "contents": {
                "scripts": scripts,
                "playbooks": playbooks,
                "workflows": workflows
            },
            "file_hashes": file_hashes,
            "signature": None  # Se añade después de firmar
        }

        # Ordenar claves para determinismo
        return json.dumps(manifest, sort_keys=True, indent=2)

    def add_signature(self, manifest_json: str, signature_data: Dict) -> str:
        """
        Añade la firma al manifiesto.

        Este método:
        1. Calcula el hash SHA256 del manifiesto original (sin firma)
        2. Añade la firma proporcionada
        3. Añade el package_hash para verificación de integridad

        Args:
            manifest_json: JSON string del manifiesto sin firmar
            signature_data: Datos de la firma (del ManifestSignatureService):
                {
                    "type": "CLIENT" | "PARTNER",
                    "algorithm": "HMAC-SHA256" | "RSA-SHA256",
                    "value": "<firma>",
                    "timestamp": "<ISO timestamp>"
                }

        Returns:
            str: JSON del manifiesto con firma añadida
        """
        # Parsear manifiesto
        manifest = json.loads(manifest_json)

        # Calcular hash del manifiesto original (antes de añadir firma)
        package_hash = hashlib.sha256(manifest_json.encode()).hexdigest()

        # Añadir firma y hash
        manifest["signature"] = signature_data
        manifest["package_hash"] = package_hash

        # Retornar con claves ordenadas para consistencia
        return json.dumps(manifest, sort_keys=True, indent=2)


# Singleton del generador
manifest_generator = ManifestGenerator()
