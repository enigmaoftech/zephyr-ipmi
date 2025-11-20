"""Security helpers for password hashing, encryption, and session signing."""
from __future__ import annotations

import base64
import hashlib
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from .config import get_settings


_password_context = CryptContext(schemes=["argon2"], deprecated="auto")


class PasswordHasher:
    """Hash and verify user passwords using Argon2id."""

    @staticmethod
    def hash(password: str) -> str:
        return _password_context.hash(password)

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        return _password_context.verify(password, hashed)


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class SecretManager:
    """Encrypt and decrypt sensitive secrets with Fernet."""

    def __init__(self, key: str | None = None) -> None:
        settings = get_settings()
        raw_key = key or settings.encryption_key or settings.secret_key
        derived = _derive_fernet_key(raw_key)
        self._fernet = Fernet(derived)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encryption token") from exc


class SessionSigner:
    """Sign and unsign short-lived session payloads."""

    def __init__(self, salt: str = "zephyr-session") -> None:
        settings = get_settings()
        self._serializer = URLSafeTimedSerializer(settings.secret_key, salt=salt)

    def dumps(self, data: dict[str, Any]) -> str:
        return self._serializer.dumps(data)

    def loads(self, token: str, max_age: int | None = None) -> dict[str, Any]:
        try:
            return self._serializer.loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired) as exc:
            raise ValueError("Invalid or expired session token") from exc
