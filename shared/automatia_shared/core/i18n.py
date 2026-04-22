"""
Internationalization (i18n) module for AutomatIA.
Loads translations from JSON files and provides translation functions.
"""

import os
import json
from pathlib import Path


class I18nManager:
    """
    Gestor central de internacionalización (i18n).
    
    Se encarga de cargar traducciones desde archivos JSON distribuidos en el proyecto
    y proporcionar una interfaz para recuperar cadenas traducidas basadas en el local actual.
    """
    def __init__(self):
        """
        Inicializa el gestor y establece el idioma por defecto (es).
        La carga de traducciones se realiza de forma perezosa (lazy).
        """
        self.translations = {}
        self.locale = 'es'  # Default
        self._initialized = False

    def _ensure_initialized(self):
        """Garantiza que las traducciones estén cargadas antes de su uso."""
        if not self._initialized:
            self._load_translations()
            self._initialized = True

    def _deep_update(self, base_dict: dict, update_dict: dict):
        """
        Realiza una actualización profunda (recursiva) de un diccionario.
        Se usa para fusionar traducciones de diferentes archivos sin sobrescribir
        ramas enteras del árbol de traducción.
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def _load_translations(self):
        """Recursive load of translations.json."""
        root = Path(os.getcwd())

        # 1. Base translations
        base_path = root / "translations.json"
        if base_path.exists():
            try:
                with open(base_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
            except Exception as e:
                print(f"[I18n] Error loading base translations: {e}")

        # 2. Module translations (Recursive search in app/ and client_app/ and server/)
        for app_dir_name in ["app", "client_app", "server"]:
            app_dir = root / app_dir_name
            if app_dir.exists():
                for path in app_dir.rglob("*translations.json"):
                    if path.resolve() == base_path.resolve():
                        continue

                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            # Structure is {lang: {key: val}}
                            for lang, keys in data.items():
                                if lang not in self.translations:
                                    self.translations[lang] = {}
                                self._deep_update(self.translations[lang], keys)
                    except Exception as e:
                        print(f"[I18n] Error loading {path}: {e}")
                    except Exception as e:
                        print(f"[I18n] Error loading {path}: {e}")

        print(f"[I18n] Loaded {sum(len(k) for k in self.translations.values())} keys.")

    def set_locale(self, locale: str):
        """Set the current locale."""
        self._ensure_initialized()
        self.locale = locale

    def t(self, key: str, default: str = None, **kwargs) -> str:
        """Translate a key with optional format arguments. Supports dot notation (e.g. 'admin.title').

        Args:
            key: Translation key (e.g. 'admin.title')
            default: Optional default value if key not found
            **kwargs: Format arguments for the translation string
        """
        self._ensure_initialized()
        def get_nested(d: dict, k_str: str):
            """
            Resuelve una clave usando notación de puntos (ej: 'auth.login.title')
            navegando por la estructura anidada de diccionarios.
            """
            if not isinstance(d, dict):
                return None
            parts = k_str.split('.')
            val = d
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    return None
            return val if not isinstance(val, dict) else None # Return None if result is still a dict (not a leaf string)

        val = get_nested(self.translations.get(self.locale, {}), key)

        # Fallback to ES if key missing in current locale
        if val is None and self.locale != 'es':
            val = get_nested(self.translations.get('es', {}), key)

        if val is None:
            # Last ditch: check if key exists as a flat key (legacy support)
            val = self.translations.get(self.locale, {}).get(key)

        if val is None:
            # Use provided default or fall back to key
            return default if default is not None else key

        try:
            return str(val).format(**kwargs)
        except:
            return str(val)


# Global Instance
i18n = I18nManager()


def t(key: str, default: str = None, **kwargs) -> str:
    """Convenience function for translation."""
    return i18n.t(key, default, **kwargs)
