import os
from pathlib import Path
from typing import Optional
from client_app.app.services.config_service import config_service
from shared.automatia_shared.crypto_utils import rsa_signer

class DevCryptoService:
    """
    Servicio de gestión de llaves RSA de desarrollo locales.
    Solo genera y carga llaves si DEBUG_MODE=True.
    """
    def __init__(self):
        self.debug_mode = config_service.get_bool("DEBUG_MODE")
        self.keys_dir = config_service.get_path("DEV_KEYS_DIR")
        self.private_key_path = self.keys_dir / "private.pem"
        self.public_key_path = self.keys_dir / "public.pem"
        
        if self.debug_mode:
            self._ensure_keys()

    def _ensure_keys(self):
        """Asegura que las llaves existan, generándolas si es necesario."""
        if not self.keys_dir.exists():
            self.keys_dir.mkdir(parents=True, exist_ok=True)
            
        if not self.private_key_path.exists() or not self.public_key_path.exists():
            print("[DevCrypto] Generando nuevas llaves RSA de desarrollo...")
            private_pem, public_pem = rsa_signer.generate_key_pair(2048)
            
            # Guardar con permisos restrictivos
            with open(self.private_key_path, "wb") as f:
                f.write(private_pem)
            
            with open(self.public_key_path, "wb") as f:
                f.write(public_pem)
            
            # Intentar establecer permisos restrictivos (POSIX)
            try:
                os.chmod(self.private_key_path, 0o600)
                os.chmod(self.public_key_path, 0o644)
            except Exception:
                pass # Ignorar fallos de chmod en sistemas no POSIX (Windows)

    def get_private_key(self) -> Optional[bytes]:
        """Retorna la llave privada en formato PEM."""
        if not self.debug_mode or not self.private_key_path.exists():
            return None
        return self.private_key_path.read_bytes()

    def get_public_key(self) -> Optional[bytes]:
        """Retorna la llave pública en formato PEM."""
        if not self.debug_mode or not self.public_key_path.exists():
            return None
        return self.public_key_path.read_bytes()

# Global instance
dev_crypto_service = DevCryptoService()
