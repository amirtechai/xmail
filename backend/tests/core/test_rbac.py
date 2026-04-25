"""Unit tests for RBAC dependencies (require_admin, require_operator)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.deps import require_admin, require_operator
from app.models.user import User, UserRole


def _make_user(role: str, is_active: bool = True) -> User:
    u = MagicMock(spec=User)
    u.id = str(uuid.uuid4())
    u.role = role
    u.is_active = is_active
    return u


# ── require_admin ─────────────────────────────────────────────────────────────

class TestRequireAdmin:
    @pytest.mark.asyncio
    async def test_admin_passes(self):
        user = _make_user(UserRole.ADMIN.value)
        result = await require_admin(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_operator_rejected(self):
        user = _make_user(UserRole.OPERATOR.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_rejected(self):
        user = _make_user(UserRole.VIEWER.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_legacy_user_role_rejected(self):
        user = _make_user(UserRole.USER.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_detail_message(self):
        user = _make_user(UserRole.VIEWER.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user)
        assert "Admin" in exc_info.value.detail


# ── require_operator ──────────────────────────────────────────────────────────

class TestRequireOperator:
    @pytest.mark.asyncio
    async def test_admin_passes(self):
        user = _make_user(UserRole.ADMIN.value)
        result = await require_operator(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_operator_passes(self):
        user = _make_user(UserRole.OPERATOR.value)
        result = await require_operator(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_viewer_rejected(self):
        user = _make_user(UserRole.VIEWER.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_operator(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_legacy_user_role_rejected(self):
        user = _make_user(UserRole.USER.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_operator(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_detail_message(self):
        user = _make_user(UserRole.VIEWER.value)
        with pytest.raises(HTTPException) as exc_info:
            await require_operator(user)
        assert "Operator" in exc_info.value.detail
