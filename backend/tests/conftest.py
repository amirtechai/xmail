"""Shared fixtures for all test modules."""

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.models.user import User, UserRole

# ── Test user factory ─────────────────────────────────────────────────────────


def make_user(
    email: str = "test@example.com",
    role: str = UserRole.ADMIN.value,
    password: str | None = None,
    is_active: bool = True,
    totp_enabled: bool = False,
) -> User:
    import os

    raw_pw = password or os.environ.get("TEST_USER_PASSWORD") or os.urandom(16).hex()
    user = User()
    user.id = uuid.uuid4()
    user.email = email
    user.full_name = "Test User"
    user.password_hash = hash_password(raw_pw)
    user.role = role
    user.is_active = is_active
    user.totp_enabled = totp_enabled
    user.totp_secret_encrypted = None
    user.failed_login_count = 0
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.last_login_at = None
    return user


@pytest.fixture
def test_user() -> User:
    return make_user()


@pytest.fixture
def admin_user() -> User:
    return make_user(email="admin@example.com", role=UserRole.ADMIN.value)


# ── Mock session ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _make_scalar_result(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = [value] if value is not None else []
    return result


@pytest.fixture
def make_scalar_result():
    return _make_scalar_result


# ── Auth token helper ─────────────────────────────────────────────────────────


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    from app.core.auth import create_access_token

    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
