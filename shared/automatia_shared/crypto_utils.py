"""
Utilidades criptográficas para firma y verificación RSA.

Este módulo proporciona las herramientas de firma digital utilizadas para garantizar
la integridad y autenticidad de los manifiestos y scripts intercambiados entre
el servidor Brain y los clientes AutomatIA.

Utiliza RSA con PSS padding y SHA256 para máxima seguridad.
"""

import base64
import json
from typing import Any, Dict, Tuple, Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.exceptions import InvalidSignature


class SignatureVerificationError(Exception):
    """Excepción lanzada cuando la verificación de firma falla."""
    pass


class InvalidKeyError(Exception):
    """Excepción lanzada cuando una clave RSA es inválida o está corrupta."""
    pass


class RSASigner:
    """
    Clase para firma y verificación RSA de payloads.

    Utiliza RSA-PSS con SHA256 para firmas digitales seguras.
    PSS (Probabilistic Signature Scheme) es el estándar recomendado
    para firmas RSA modernas, más seguro que PKCS#1 v1.5.

    Ejemplo de uso:
        >>> signer = RSASigner()
        >>> signature = signer.sign_payload('{"data": "test"}', private_key_pem)
        >>> is_valid = signer.verify_signature('{"data": "test"}', signature, public_key_pem)
    """

    # Configuración de padding PSS con SHA256
    _PADDING = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    )
    _HASH_ALGORITHM = hashes.SHA256()

    def sign_payload(self, payload: str, private_key_pem: bytes) -> str:
        """
        Firma un payload string con una clave privada RSA.

        Args:
            payload: String a firmar (típicamente un JSON serializado).
            private_key_pem: Clave privada RSA en formato PEM (bytes).

        Returns:
            str: Firma codificada en Base64.

        Raises:
            InvalidKeyError: Si la clave privada es inválida o está corrupta.
            ValueError: Si el payload está vacío.
        """
        if not payload:
            raise ValueError("El payload no puede estar vacío")

        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None
            )
        except Exception as e:
            raise InvalidKeyError(f"Clave privada inválida: {e}") from e

        if not isinstance(private_key, RSAPrivateKey):
            raise InvalidKeyError("La clave proporcionada no es una clave privada RSA")

        # Firmar el payload
        signature_bytes = private_key.sign(
            payload.encode('utf-8'),
            self._PADDING,
            self._HASH_ALGORITHM
        )

        # Retornar en Base64 para facilitar transporte JSON
        return base64.b64encode(signature_bytes).decode('utf-8')

    def verify_signature(
        self,
        payload: str,
        signature_b64: str,
        public_key_pem: bytes
    ) -> bool:
        """
        Verifica la firma de un payload usando una clave pública RSA.

        Args:
            payload: String original que fue firmado.
            signature_b64: Firma en formato Base64.
            public_key_pem: Clave pública RSA en formato PEM (bytes).

        Returns:
            bool: True si la firma es válida, False en caso contrario.

        Raises:
            InvalidKeyError: Si la clave pública es inválida o está corrupta.
            ValueError: Si la firma Base64 está malformada.
        """
        if not payload or not signature_b64:
            return False

        try:
            public_key = serialization.load_pem_public_key(public_key_pem)
        except Exception as e:
            raise InvalidKeyError(f"Clave pública inválida: {e}") from e

        if not isinstance(public_key, RSAPublicKey):
            raise InvalidKeyError("La clave proporcionada no es una clave pública RSA")

        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            raise ValueError(f"Firma Base64 malformada: {e}") from e

        try:
            public_key.verify(
                signature_bytes,
                payload.encode('utf-8'),
                self._PADDING,
                self._HASH_ALGORITHM
            )
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def canonicalize_json(data: Union[Dict[str, Any], list]) -> str:
        """
        Serializa un diccionario o lista a JSON de forma canónica (determinista).

        Garantiza que el mismo contenido siempre produzca el mismo string JSON,
        independientemente del orden de inserción de las claves. Esto es crítico
        para que las firmas sean consistentes.

        Args:
            data: Diccionario o lista a serializar.

        Returns:
            str: JSON serializado de forma canónica.
        """
        return json.dumps(
            data,
            sort_keys=True,
            separators=(',', ':'),  # Sin espacios extra
            ensure_ascii=False
        )

    @staticmethod
    def generate_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        Genera un nuevo par de claves RSA.

        Útil para desarrollo, testing y generación inicial de claves de Partner.

        Args:
            key_size: Tamaño de la clave en bits (default: 2048).
                      Usar 4096 para mayor seguridad en producción.

        Returns:
            Tuple[bytes, bytes]: (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem


# Instancia singleton para uso conveniente
rsa_signer = RSASigner()


__all__ = [
    "RSASigner",
    "rsa_signer",
    "SignatureVerificationError",
    "InvalidKeyError",
]
