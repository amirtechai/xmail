"""Fernet-based symmetric encryption for sensitive fields (API keys, SMTP passwords)."""

import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet-compatible key from an arbitrary secret string."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


class CryptoManager:
    def __init__(self, secret_key: str) -> None:
        self._cipher = Fernet(_derive_key(secret_key))

    def encrypt(self, plaintext: str) -> bytes:
        return self._cipher.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        return self._cipher.decrypt(ciphertext).decode()


# Lazy singleton — initialised after settings are loaded
_manager: CryptoManager | None = None


def get_crypto() -> CryptoManager:
    global _manager
    if _manager is None:
        from app.config import settings  # avoid circular import at module level

        _manager = CryptoManager(settings.secret_key)
    return _manager
