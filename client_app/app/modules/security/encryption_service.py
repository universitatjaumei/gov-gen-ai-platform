"""
Encryption service for secure credential storage.

Uses Fernet symmetric encryption for storing sensitive data
like IMAP/SMTP credentials, API keys, etc.
"""
import os
import json
from pathlib import Path
from typing import Any, Dict
from cryptography.fernet import Fernet

# Path to store the encryption key (in data directory)
KEY_FILE_PATH = Path("data") / ".encryption_key"


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet (AES-128-CBC with HMAC-SHA256) for secure encryption.
    The encryption key is read from:
    1. AUTOMATIA_SECRET_KEY environment variable (priority)
    2. data/.encryption_key file (persistent across sessions)
    3. Generated new and saved to file (first run only)

    Usage:
        service = EncryptionService()
        encrypted = service.encrypt({"user": "admin", "pass": "secret"})
        decrypted = service.decrypt(encrypted)
    """

    def __init__(self):
        """Initialize encryption service with persistent key."""
        key = self._get_or_create_key()
        self.cipher = Fernet(key)

    def _get_or_create_key(self) -> bytes:
        """
        Get encryption key from environment, file, or generate new.

        Priority:
        1. AUTOMATIA_SECRET_KEY environment variable
        2. Existing key file
        3. Generate new key and save to file
        """
        # 1. Check environment variable
        env_key = os.environ.get("AUTOMATIA_SECRET_KEY")
        if env_key:
            return env_key.encode() if isinstance(env_key, str) else env_key

        # 2. Check key file
        if KEY_FILE_PATH.exists():
            try:
                key = KEY_FILE_PATH.read_bytes().strip()
                # Validate it's a valid Fernet key
                Fernet(key)
                return key
            except Exception:
                # Corrupted key file, will regenerate
                pass

        # 3. Generate new key and save
        new_key = Fernet.generate_key()
        self._save_key(new_key)
        return new_key

    def _save_key(self, key: bytes) -> None:
        """Save encryption key to file."""
        try:
            KEY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            KEY_FILE_PATH.write_bytes(key)
            # Set restrictive permissions on Unix systems
            if os.name != 'nt':
                os.chmod(KEY_FILE_PATH, 0o600)
        except Exception as e:
            print(f"[EncryptionService] Warning: Could not save key to file: {e}")

    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary to a Fernet-encrypted string.

        Args:
            data: Dictionary containing sensitive data to encrypt

        Returns:
            str: Base64-encoded encrypted string
        """
        json_str = json.dumps(data)
        encrypted_bytes = self.cipher.encrypt(json_str.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt a Fernet-encrypted string back to dictionary.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Dict: Original dictionary data

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted_bytes.decode())

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Use this to create a key for AUTOMATIA_SECRET_KEY environment variable.

        Returns:
            str: Base64-encoded 32-byte key
        """
        return Fernet.generate_key().decode()
