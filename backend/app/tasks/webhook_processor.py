"""Celery task: process a single normalised webhook event.

Called by the webhook routes after signature verification.
Payload is a dict with keys:
    provider    : "sendgrid" | "postmark" | "mailgun"
    event_type  : "bounce" | "open" | "click" | "unsubscribe" | "complaint"
    email       : recipient address
    message_id  : provider message-id (used to look up SentEmail)
    timestamp   : ISO-8601 string (UTC)
    extra       : dict (provider-specific fields, e.g. URL for clicks)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.webhook_processor.process_webhook_event",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_webhook_event(self, payload: dict) -> dict:  # type: ignore[override]
    try:
        return asyncio.get_event_loop().run_until_complete(_process(payload))
    except Exception as exc:
        logger.warning("webhook_processor_retry", reason=str(exc), payload=payload)
        raise self.retry(exc=exc)


async def _process(payload: dict) -> dict:
    from sqlalchemy import select, update
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.database import async_session_factory
    from app.deduplication.hasher import hash_email
    from app.models.sent_email import SentEmail, SentEmailStatus
    from app.models.suppression_list import SuppressionList, SuppressionReason

    event_type = payload.get("event_type", "")
    email = (payload.get("email") or "").lower().strip()
    message_id = payload.get("message_id") or ""
    raw_ts = payload.get("timestamp") or ""
    extra = payload.get("extra") or {}

    try:
        event_time = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        event_time = datetime.utcnow()

    async with async_session_factory() as session:
        # Resolve the SentEmail row (look up by message_id first, then by email)
        sent_email: SentEmail | None = None
        if message_id:
            result = await session.execute(
                select(SentEmail).where(SentEmail.message_id == message_id).limit(1)
            )
            sent_email = result.scalar_one_or_none()

        if event_type == "bounce":
            await _handle_bounce(session, sent_email, email, event_time, pg_insert, SuppressionList, SuppressionReason, SentEmailStatus, hash_email)

        elif event_type == "open":
            await _handle_open(session, sent_email, email, event_time, SentEmailStatus)

        elif event_type == "click":
            url = extra.get("url", "")
            await _handle_click(session, sent_email, email, event_time, url, SentEmailStatus)

        elif event_type in ("unsubscribe", "complaint"):
            reason = SuppressionReason.COMPLAINED if event_type == "complaint" else SuppressionReason.UNSUBSCRIBED
            await _suppress(session, email, reason, sent_email, pg_insert, SuppressionList, hash_email)
            if sent_email:
                await session.execute(
                    update(SentEmail)
                    .where(SentEmail.id == sent_email.id)
                    .values(status=SentEmailStatus.UNSUBSCRIBED.value)
                )

        await session.commit()

    logger.info("webhook_processed", event_type=event_type, email=email, message_id=message_id)
    return {"event_type": event_type, "email": email}


async def _handle_bounce(session, sent_email, email, event_time, pg_insert, SuppressionList, SuppressionReason, SentEmailStatus, hash_email):
    from sqlalchemy import update
    from app.models.sent_email import SentEmail

    if sent_email:
        await session.execute(
            update(SentEmail)
            .where(SentEmail.id == sent_email.id)
            .values(status=SentEmailStatus.BOUNCED.value, bounce_processed=True)
        )
    await _suppress(session, email, SuppressionReason.BOUNCED, sent_email, pg_insert, SuppressionList, hash_email)


async def _handle_open(session, sent_email, email, event_time, SentEmailStatus):
    from sqlalchemy import update
    from app.models.sent_email import SentEmail

    if sent_email and not sent_email.opened_at:
        await session.execute(
            update(SentEmail)
            .where(SentEmail.id == sent_email.id)
            .values(status=SentEmailStatus.OPENED.value, opened_at=event_time)
        )


async def _handle_click(session, sent_email, email, event_time, url, SentEmailStatus):
    from sqlalchemy import update
    from app.models.sent_email import SentEmail

    if sent_email:
        existing_clicks = list(sent_email.click_events or [])
        existing_clicks.append({"url": url, "timestamp": event_time.isoformat()})
        values: dict = {"status": SentEmailStatus.CLICKED.value, "click_events": existing_clicks}
        if not sent_email.clicked_at:
            values["clicked_at"] = event_time
        await session.execute(
            update(SentEmail).where(SentEmail.id == sent_email.id).values(**values)
        )


async def _suppress(session, email, reason, sent_email, pg_insert, SuppressionList, hash_email):
    if not email:
        return
    from app.deduplication.hasher import hash_email as _hash
    stmt = (
        pg_insert(SuppressionList)
        .values(
            email=email,
            email_hash=_hash(email),
            reason=reason,
            source_campaign_id=sent_email.campaign_id if sent_email else None,
        )
        .on_conflict_do_nothing(index_elements=["email_hash"])
    )
    await session.execute(stmt)
