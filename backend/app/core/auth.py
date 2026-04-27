"""JWT authentication helpers."""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(plain: str) -> str:
    # cost factor 12 — ~250ms on modern hardware, enough to slow offline attacks
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=7)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """Raises JWTError if invalid/expired."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def get_subject(token: str) -> str | None:
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None
