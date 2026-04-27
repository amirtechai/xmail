"""Integration tests for /api/auth endpoints using mocked DB session."""

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest
from httpx import AsyncClient

from app.core.auth import create_access_token, hash_password
from tests.conftest import make_user

# ── /api/auth/login ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success(
    async_client: AsyncClient, mock_session: AsyncMock, make_scalar_result
):
    user = make_user(password="ValidP@ss1!")
    user.password_hash = hash_password("ValidP@ss1!")
    mock_session.execute.return_value = make_scalar_result(user)

    with patch("app.api.routes.auth._get_redis", return_value=_make_redis_mock()):
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "ValidP@ss1!"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] is not None
    assert data["requires_totp"] is False


def _make_redis_mock(locked: bool = False) -> AsyncMock:
    """Build a Redis mock that handles pipeline().incr/expire/execute correctly.

    redis.pipeline() is a synchronous call in aioredis — it returns a Pipeline
    object (not a coroutine). We must set it as a MagicMock so AsyncMock doesn't
    wrap it in a coroutine automatically.
    """
    # pipeline() itself is synchronous; incr/expire/execute are awaited
    pipeline = MagicMock()
    pipeline.incr = AsyncMock(return_value=None)
    pipeline.expire = AsyncMock(return_value=None)
    pipeline.execute = AsyncMock(return_value=[1])

    redis_mock = AsyncMock()
    redis_mock.exists.return_value = 1 if locked else 0
    redis_mock.pipeline = MagicMock(return_value=pipeline)  # sync, not async

    return redis_mock


@pytest.mark.asyncio
async def test_login_wrong_password(
    async_client: AsyncClient, mock_session: AsyncMock, make_scalar_result
):
    user = make_user(password="CorrectPass1!")
    user.password_hash = hash_password("CorrectPass1!")
    mock_session.execute.return_value = make_scalar_result(user)

    with patch("app.api.routes.auth._get_redis", return_value=_make_redis_mock()):
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "WrongPass1!"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(
    async_client: AsyncClient, mock_session: AsyncMock, make_scalar_result
):
    mock_session.execute.return_value = make_scalar_result(None)

    with patch("app.api.routes.auth._get_redis", return_value=_make_redis_mock()):
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "SomePass1!"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_locked_account(
    async_client: AsyncClient, mock_session: AsyncMock, make_scalar_result
):
    user = make_user()
    mock_session.execute.return_value = make_scalar_result(user)

    with patch("app.api.routes.auth._get_redis") as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.exists.return_value = 1  # locked
        mock_redis.return_value = redis_mock

        resp = await async_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "AnyPass1!"},
        )

    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_login_requires_totp(
    async_client: AsyncClient, mock_session: AsyncMock, make_scalar_result
):
    user = make_user(password="ValidP@ss1!", totp_enabled=True)
    user.password_hash = hash_password("ValidP@ss1!")
    mock_session.execute.return_value = make_scalar_result(user)

    with patch("app.api.routes.auth._get_redis", return_value=_make_redis_mock()):
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "ValidP@ss1!"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["requires_totp"] is True
    assert data["totp_token"] is not None
    assert data["access_token"] is None


# ── /api/auth/me ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_returns_user(
    async_client: AsyncClient, mock_session: AsyncMock, make_scalar_result, test_user
):
    mock_session.execute.return_value = make_scalar_result(test_user)
    token = create_access_token(str(test_user.id))

    resp = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["email"] == test_user.email


@pytest.mark.asyncio
async def test_me_unauthorized_without_token(async_client: AsyncClient):
    resp = await async_client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(async_client: AsyncClient):
    resp = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401
