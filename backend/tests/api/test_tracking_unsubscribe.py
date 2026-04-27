"""Tests for open-tracking pixel (/t/o/...) and unsubscribe (/u/...) endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _scalar_result(value: object) -> MagicMock:
    """Sync MagicMock result so scalar_one_or_none() doesn't return a coroutine."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ── minimal app ────────────────────────────────────────────────────────────────


def _build_app() -> FastAPI:
    app = FastAPI()
    from app.core.exceptions import register_exception_handlers

    register_exception_handlers(app)
    from app.api.routes.tracking import router as tracking_router
    from app.api.routes.unsubscribe import router as unsubscribe_router

    app.include_router(tracking_router)
    app.include_router(unsubscribe_router)
    return app


@pytest.fixture(scope="module")
def pub_app() -> FastAPI:
    return _build_app()


@pytest.fixture
async def client(pub_app: FastAPI, mock_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    from app.database import get_session

    async def _override() -> AsyncGenerator:
        yield mock_session

    pub_app.dependency_overrides[get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=pub_app), base_url="http://test") as c:
        yield c
    pub_app.dependency_overrides.clear()


# ── tracking pixel ─────────────────────────────────────────────────────────────


class TestTrackingPixel:
    async def test_bad_uuid_returns_gif(self, client: AsyncClient) -> None:
        r = await client.get("/t/o/not-a-uuid.gif")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/gif"

    async def test_unknown_uuid_returns_gif(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _scalar_result(None)

        r = await client.get(f"/t/o/{uuid.uuid4()}.gif")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/gif"

    async def test_first_open_marks_opened(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        from app.models.sent_email import SentEmailStatus

        sent = MagicMock()
        sent.tracking_pixel_opened_at = None
        sent.status = SentEmailStatus.SENT.value
        mock_session.execute.return_value = _scalar_result(sent)

        r = await client.get(f"/t/o/{uuid.uuid4()}.gif")
        assert r.status_code == 200
        assert sent.tracking_pixel_opened_at is not None
        assert sent.status == SentEmailStatus.OPENED.value
        mock_session.commit.assert_called_once()

    async def test_second_open_idempotent(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        from datetime import datetime

        from app.models.sent_email import SentEmailStatus

        mock_session.reset_mock()
        sent = MagicMock()
        sent.tracking_pixel_opened_at = datetime.utcnow()
        sent.status = SentEmailStatus.OPENED.value
        mock_session.execute.return_value = _scalar_result(sent)

        r = await client.get(f"/t/o/{uuid.uuid4()}.gif")
        assert r.status_code == 200
        mock_session.commit.assert_not_called()

    async def test_no_cache_header(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        mock_session.execute.return_value = _scalar_result(None)
        r = await client.get(f"/t/o/{uuid.uuid4()}.gif")
        assert "no-store" in r.headers.get("cache-control", "")


# ── unsubscribe ────────────────────────────────────────────────────────────────


class TestUnsubscribePage:
    async def test_get_bad_token_returns_400_html(self, client: AsyncClient) -> None:
        r = await client.get("/u/not-a-uuid")
        assert r.status_code == 400
        assert "text/html" in r.headers["content-type"]

    async def test_get_valid_token_returns_confirm_form(self, client: AsyncClient) -> None:
        r = await client.get(f"/u/{uuid.uuid4()}")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Confirm Unsubscribe" in r.text

    async def test_post_bad_token_returns_400(self, client: AsyncClient) -> None:
        r = await client.post("/u/not-a-uuid")
        assert r.status_code == 400

    async def test_post_unknown_token_returns_already_processed(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _scalar_result(None)
        r = await client.post(f"/u/{uuid.uuid4()}")
        assert r.status_code == 200
        assert "already" in r.text.lower()

    async def test_post_valid_token_unsubscribes(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        from app.models.sent_email import SentEmailStatus
        from app.models.suppression_list import SuppressionList

        mock_session.reset_mock()
        sent = MagicMock()
        sent.recipient_email = "user@example.com"
        sent.status = SentEmailStatus.SENT.value

        mock_session.execute.side_effect = [_scalar_result(sent), _scalar_result(None)]

        r = await client.post(f"/u/{uuid.uuid4()}")
        assert r.status_code == 200
        assert "unsubscribed" in r.text.lower()
        assert "user@example.com" in r.text
        assert sent.status == SentEmailStatus.UNSUBSCRIBED.value
        mock_session.add.assert_called_once()
        added: SuppressionList = mock_session.add.call_args[0][0]
        assert added.email == "user@example.com"
        mock_session.commit.assert_called_once()

    async def test_post_bounced_email_skips_status_change(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        from app.models.sent_email import SentEmailStatus

        mock_session.reset_mock()
        sent = MagicMock()
        sent.recipient_email = "bounced@example.com"
        sent.status = SentEmailStatus.BOUNCED.value

        mock_session.execute.side_effect = [_scalar_result(sent), _scalar_result(None)]

        await client.post(f"/u/{uuid.uuid4()}")
        assert sent.status == SentEmailStatus.BOUNCED.value

    async def test_post_already_suppressed_no_duplicate(
        self, client: AsyncClient, mock_session: AsyncMock
    ) -> None:
        from app.models.sent_email import SentEmailStatus
        from app.models.suppression_list import SuppressionList

        mock_session.reset_mock()
        sent = MagicMock()
        sent.recipient_email = "already@example.com"
        sent.status = SentEmailStatus.SENT.value

        existing = MagicMock(spec=SuppressionList)
        mock_session.execute.side_effect = [_scalar_result(sent), _scalar_result(existing)]

        await client.post(f"/u/{uuid.uuid4()}")
        mock_session.add.assert_not_called()
