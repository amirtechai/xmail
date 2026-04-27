"""Webhook receiver endpoints for SendGrid, Postmark, and Mailgun.

Each endpoint:
1. Verifies HMAC/ECDSA signature (403 if wrong; skip if key not configured)
2. Normalises the provider payload into a canonical dict
3. Dispatches a Celery task for async processing
4. Returns 200 immediately (providers expect fast ACK)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import settings
from app.core.webhook_signatures import verify_mailgun, verify_postmark, verify_sendgrid

from app.core.logger import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# ── helpers ────────────────────────────────────────────────────────────────────


def _dispatch(provider: str, event_type: str, email: str, message_id: str, ts: str, extra: dict) -> None:
    from app.tasks.webhook_processor import process_webhook_event

    process_webhook_event.delay(
        {
            "provider": provider,
            "event_type": event_type,
            "email": email,
            "message_id": message_id,
            "timestamp": ts,
            "extra": extra,
        }
    )


def _utc_iso(ts: Any) -> str:
    """Convert Unix timestamp or ISO string to UTC ISO-8601 string."""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return str(ts)


# ── SendGrid ──────────────────────────────────────────────────────────────────

_SENDGRID_EVENT_MAP = {
    "bounce": "bounce",
    "blocked": "bounce",
    "open": "open",
    "click": "click",
    "unsubscribe": "unsubscribe",
    "spamreport": "complaint",
}


@router.post("/sendgrid", status_code=status.HTTP_200_OK)
async def sendgrid_webhook(
    request: Request,
    x_twilio_email_event_webhook_signature: str | None = Header(default=None),
    x_twilio_email_event_webhook_timestamp: str | None = Header(default=None),
) -> dict:
    raw_body = await request.body()

    if settings.sendgrid_webhook_public_key:
        if not (x_twilio_email_event_webhook_signature and x_twilio_email_event_webhook_timestamp):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing signature headers")
        if not verify_sendgrid(raw_body, x_twilio_email_event_webhook_signature, x_twilio_email_event_webhook_timestamp, settings.sendgrid_webhook_public_key):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    else:
        logger.warning("sendgrid_webhook_no_key_configured")

    try:
        events: list[dict] = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    dispatched = 0
    for ev in events:
        raw_type = ev.get("event", "")
        event_type = _SENDGRID_EVENT_MAP.get(raw_type)
        if not event_type:
            continue
        email = ev.get("email", "")
        message_id = ev.get("sg_message_id", "")
        ts = _utc_iso(ev.get("timestamp", 0))
        extra: dict = {}
        if event_type == "click":
            extra["url"] = ev.get("url", "")
        _dispatch("sendgrid", event_type, email, message_id, ts, extra)
        dispatched += 1

    return {"queued": dispatched}


# ── Postmark ──────────────────────────────────────────────────────────────────

_POSTMARK_EVENT_MAP = {
    "Bounce": "bounce",
    "Open": "open",
    "Click": "click",
    "SpamComplaint": "complaint",
    "SubscriptionChange": "unsubscribe",
}


@router.post("/postmark", status_code=status.HTTP_200_OK)
async def postmark_webhook(
    request: Request,
    x_postmark_token: str | None = Header(default=None),
) -> dict:
    if settings.postmark_webhook_token:
        if not verify_postmark(x_postmark_token, settings.postmark_webhook_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    else:
        logger.warning("postmark_webhook_no_token_configured")

    try:
        ev: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    record_type = ev.get("RecordType", "")
    event_type = _POSTMARK_EVENT_MAP.get(record_type)
    if not event_type:
        return {"queued": 0}

    email = ev.get("Email") or ev.get("Recipient", "")
    message_id = ev.get("MessageID", "")
    raw_ts = ev.get("BouncedAt") or ev.get("ReceivedAt") or ev.get("DeliveredAt") or datetime.utcnow().isoformat()
    extra: dict = {}
    if event_type == "click":
        extra["url"] = ev.get("OriginalLink", "")

    _dispatch("postmark", event_type, email, message_id, raw_ts, extra)
    return {"queued": 1}


# ── Mailgun ───────────────────────────────────────────────────────────────────

_MAILGUN_EVENT_MAP = {
    "failed": "bounce",
    "opened": "open",
    "clicked": "click",
    "unsubscribed": "unsubscribe",
    "complained": "complaint",
}


@router.post("/mailgun", status_code=status.HTTP_200_OK)
async def mailgun_webhook(request: Request) -> dict:
    try:
        body: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    sig_block = body.get("signature", {})
    timestamp = str(sig_block.get("timestamp", ""))
    token = str(sig_block.get("token", ""))
    signature = str(sig_block.get("signature", ""))

    if settings.mailgun_webhook_signing_key:
        if not verify_mailgun(timestamp, token, signature, settings.mailgun_webhook_signing_key):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    else:
        logger.warning("mailgun_webhook_no_key_configured")

    event_data = body.get("event-data", {})
    raw_type = event_data.get("event", "")
    event_type = _MAILGUN_EVENT_MAP.get(raw_type)
    if not event_type:
        return {"queued": 0}

    email = event_data.get("recipient", "")
    message_headers = event_data.get("message", {}).get("headers", {})
    message_id = message_headers.get("message-id", "")
    ts = _utc_iso(event_data.get("timestamp", datetime.utcnow().timestamp()))
    extra: dict = {}
    if event_type == "click":
        extra["url"] = event_data.get("url", "")

    _dispatch("mailgun", event_type, email, message_id, ts, extra)
    return {"queued": 1}
