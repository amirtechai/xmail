"""Integration tests for /api/webhooks/* endpoints."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

# ── minimal app fixture ────────────────────────────────────────────────────────


def _build_webhook_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://test"],
        allow_methods=["POST"],
        allow_headers=["*"],
    )
    from app.core.exceptions import register_exception_handlers

    register_exception_handlers(app)
    from app.api.routes.webhooks import router

    app.include_router(router, prefix="/api")
    return app


@pytest.fixture(scope="module")
def webhook_app() -> FastAPI:
    return _build_webhook_app()


@pytest.fixture
async def client(webhook_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=webhook_app), base_url="http://test") as c:
        yield c


# ── helpers ────────────────────────────────────────────────────────────────────


def _mg_sig(timestamp: str, token: str, key: str) -> str:
    return hmac.new(key.encode(), (timestamp + token).encode(), hashlib.sha256).hexdigest()


DISPATCH_PATH = "app.api.routes.webhooks._dispatch"


# ── SendGrid (no signing key configured) ─────────────────────────────────────


class TestSendgridWebhook:
    @pytest.fixture(autouse=True)
    def no_sg_key(self, monkeypatch):
        monkeypatch.setattr("app.api.routes.webhooks.settings.sendgrid_webhook_public_key", "")

    @pytest.mark.asyncio
    async def test_open_event_dispatched(self, client: AsyncClient):
        payload = [
            {
                "event": "open",
                "email": "user@example.com",
                "sg_message_id": "msg1",
                "timestamp": 1714000000,
            }
        ]
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/sendgrid", json=payload)
        assert resp.status_code == 200
        assert resp.json()["queued"] == 1
        mock_dispatch.assert_called_once_with(
            "sendgrid", "open", "user@example.com", "msg1", mock_dispatch.call_args[0][4], {}
        )

    @pytest.mark.asyncio
    async def test_click_event_includes_url(self, client: AsyncClient):
        payload = [
            {
                "event": "click",
                "email": "u@e.com",
                "sg_message_id": "m2",
                "timestamp": 1714000001,
                "url": "https://example.com",
            }
        ]
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/sendgrid", json=payload)
        assert resp.status_code == 200
        _a, _b, _c, _d, _e, extra = mock_dispatch.call_args[0]
        assert extra["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_unknown_event_skipped(self, client: AsyncClient):
        payload = [
            {"event": "delivered", "email": "u@e.com", "sg_message_id": "m3", "timestamp": 0}
        ]
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/sendgrid", json=payload)
        assert resp.status_code == 200
        assert resp.json()["queued"] == 0
        mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_events(self, client: AsyncClient):
        payload = [
            {"event": "open", "email": "a@e.com", "sg_message_id": "m1", "timestamp": 1},
            {"event": "bounce", "email": "b@e.com", "sg_message_id": "m2", "timestamp": 2},
        ]
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/sendgrid", json=payload)
        assert resp.json()["queued"] == 2
        assert mock_dispatch.call_count == 2

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/webhooks/sendgrid",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400


# ── Postmark ──────────────────────────────────────────────────────────────────


class TestPostmarkWebhook:
    @pytest.fixture(autouse=True)
    def no_pm_token(self, monkeypatch):
        monkeypatch.setattr("app.api.routes.webhooks.settings.postmark_webhook_token", "")

    @pytest.mark.asyncio
    async def test_bounce_event(self, client: AsyncClient):
        payload = {
            "RecordType": "Bounce",
            "Email": "bad@bounce.com",
            "MessageID": "pm1",
            "BouncedAt": "2026-01-01T00:00:00Z",
        }
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/postmark", json=payload)
        assert resp.status_code == 200
        assert resp.json()["queued"] == 1
        mock_dispatch.assert_called_once()
        args = mock_dispatch.call_args[0]
        assert args[0] == "postmark"
        assert args[1] == "bounce"
        assert args[2] == "bad@bounce.com"

    @pytest.mark.asyncio
    async def test_unknown_record_type_returns_zero(self, client: AsyncClient):
        payload = {"RecordType": "Delivery", "Email": "ok@e.com", "MessageID": "pm2"}
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/postmark", json=payload)
        assert resp.json()["queued"] == 0
        mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_verification_rejects_wrong(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.webhooks.settings.postmark_webhook_token", "correct-token"
        )
        resp = await client.post(
            "/api/webhooks/postmark",
            json={"RecordType": "Bounce"},
            headers={"X-Postmark-Token": "wrong-token"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_token_verification_accepts_correct(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.webhooks.settings.postmark_webhook_token", "correct-token"
        )
        payload = {
            "RecordType": "Open",
            "Recipient": "u@e.com",
            "MessageID": "pm3",
            "ReceivedAt": "2026-01-01T00:00:00Z",
        }
        with patch(DISPATCH_PATH):
            resp = await client.post(
                "/api/webhooks/postmark",
                json=payload,
                headers={"X-Postmark-Token": "correct-token"},
            )
        assert resp.status_code == 200


# ── Mailgun ───────────────────────────────────────────────────────────────────


class TestMailgunWebhook:
    @pytest.fixture(autouse=True)
    def no_mg_key(self, monkeypatch):
        monkeypatch.setattr("app.api.routes.webhooks.settings.mailgun_webhook_signing_key", "")

    def _payload(self, event: str, email: str = "u@e.com", message_id: str = "mg1") -> dict:
        return {
            "signature": {"timestamp": "1714000000", "token": "tok", "signature": "sig"},
            "event-data": {
                "event": event,
                "recipient": email,
                "timestamp": 1714000000,
                "message": {"headers": {"message-id": message_id}},
            },
        }

    @pytest.mark.asyncio
    async def test_failed_event_dispatches_bounce(self, client: AsyncClient):
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/mailgun", json=self._payload("failed"))
        assert resp.status_code == 200
        args = mock_dispatch.call_args[0]
        assert args[0] == "mailgun"
        assert args[1] == "bounce"

    @pytest.mark.asyncio
    async def test_clicked_event_dispatches_click(self, client: AsyncClient):
        payload = self._payload("clicked")
        payload["event-data"]["url"] = "https://click.example.com"
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/mailgun", json=payload)
        assert resp.status_code == 200
        extra = mock_dispatch.call_args[0][5]
        assert extra["url"] == "https://click.example.com"

    @pytest.mark.asyncio
    async def test_unknown_event_returns_zero(self, client: AsyncClient):
        payload = self._payload("accepted")
        with patch(DISPATCH_PATH) as mock_dispatch:
            resp = await client.post("/api/webhooks/mailgun", json=payload)
        assert resp.json()["queued"] == 0
        mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_signature_rejects_wrong(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.webhooks.settings.mailgun_webhook_signing_key", "real-key"
        )
        payload = self._payload("opened")
        resp = await client.post("/api/webhooks/mailgun", json=payload)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_signature_accepts_correct(self, client: AsyncClient, monkeypatch):
        key = "real-key"
        monkeypatch.setattr("app.api.routes.webhooks.settings.mailgun_webhook_signing_key", key)
        ts, tok = "1714000000", "valid-token"
        sig = _mg_sig(ts, tok, key)
        payload = {
            "signature": {"timestamp": ts, "token": tok, "signature": sig},
            "event-data": {
                "event": "opened",
                "recipient": "u@e.com",
                "timestamp": 1714000000,
                "message": {"headers": {"message-id": "m1"}},
            },
        }
        with patch(DISPATCH_PATH):
            resp = await client.post("/api/webhooks/mailgun", json=payload)
        assert resp.status_code == 200
