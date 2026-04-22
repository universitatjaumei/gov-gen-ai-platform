import os
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigService:
    """
    Servicio centralizado para la gestión de configuración y rutas.
    Evita el uso de rutas "hardcoded" en los servicios.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.base_data_dir = Path(os.environ.get("STORAGE_ROOT", os.path.join(os.getcwd(), "data", "storage")))
        self.settings = {
            "DEBUG_MODE": os.environ.get("DEBUG_MODE", "True").lower() == "true",
            "CUSTOM_SCRIPTS_DIR": self.base_data_dir / "scripts" / "src",
            "CUSTOM_DOCS_DIR": self.base_data_dir / "scripts" / "docs",
            "DEV_KEYS_DIR": self.base_data_dir / "dev_keys",
            "SANDBOX_STRICT_MODE": True,
            "LOG_LEVEL": "INFO",
            "TEMP_DIR": Path(os.getcwd()) / "data" / "temp"
        }
        
        # Ensure directories exist
        for key in ["CUSTOM_SCRIPTS_DIR", "CUSTOM_DOCS_DIR", "TEMP_DIR", "DEV_KEYS_DIR"]:
            path = self.settings[key]
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def get_path(self, key: str) -> Path:
        val = self.settings.get(key)
        if val is None:
            raise KeyError(f"Configuration path key '{key}' not found")
        return Path(val)

    def get_bool(self, key: str) -> bool:
        return bool(self.settings.get(key, False))

config_service = ConfigService()
