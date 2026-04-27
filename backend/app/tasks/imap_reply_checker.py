"""IMAP reply detection task.

Polls each active SMTP config's inbox for messages whose In-Reply-To header
matches a known sent email Message-ID. On match, sets sent_email.replied_at
and status → REPLIED, which stops drip sequences (stop_on_reply=True).

Uses Python stdlib imaplib — no extra dependency required.
IMAP host is derived from the SMTP host (smtp.X → imap.X).
"""

import email
import imaplib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_SEARCH_WINDOW_DAYS = 7
_BATCH_LIMIT = 500
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="imap")


@celery_app.task(name="app.tasks.imap_reply_checker.check_imap_replies")
def check_imap_replies() -> dict:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


async def _run() -> dict:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select

    from app.config import settings
    from app.core.crypto import get_crypto
    from app.models.smtp_config import SMTPConfiguration
    from app.models.sent_email import SentEmail, SentEmailStatus

    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_replied = 0
    window_start = datetime.utcnow() - timedelta(days=_SEARCH_WINDOW_DAYS)
    crypto = get_crypto()

    async with async_session() as session:
        smtp_configs = (
            await session.execute(select(SMTPConfiguration))
        ).scalars().all()

        # Pre-fetch sent emails that could be replied to
        sent_rows = (
            await session.execute(
                select(SentEmail)
                .where(
                    SentEmail.sent_at >= window_start,
                    SentEmail.message_id.is_not(None),
                    SentEmail.replied_at.is_(None),
                )
                .limit(5000)
            )
        ).scalars().all()

        # message_id → SentEmail (strip angle brackets)
        mid_map: dict[str, SentEmail] = {
            (s.message_id or "").strip().strip("<>"): s
            for s in sent_rows
            if s.message_id
        }

        if not mid_map:
            logger.info("imap_reply_checker_no_pending")
            await engine.dispose()
            return {"replied": 0}

        for cfg in smtp_configs:
            try:
                password = crypto.decrypt(cfg.password_encrypted)
                in_reply_tos = await _fetch_inbox_reply_tos(
                    imap_host=_imap_host(cfg.host),
                    username=cfg.username,
                    password=password,
                    window_start=window_start,
                )
                for irt in in_reply_tos:
                    sent = mid_map.get(irt)
                    if sent and sent.replied_at is None:
                        sent.replied_at = datetime.utcnow()
                        sent.status = SentEmailStatus.REPLIED.value
                        total_replied += 1
            except Exception as exc:
                logger.warning("imap_check_failed", smtp_config=str(cfg.id), reason=str(exc))

        await session.commit()

    await engine.dispose()
    logger.info("imap_reply_checker_done", total_replied=total_replied)
    return {"replied": total_replied}


def _imap_host(smtp_host: str) -> str:
    if smtp_host.startswith("smtp."):
        return "imap." + smtp_host[5:]
    return smtp_host


async def _fetch_inbox_reply_tos(
    imap_host: str,
    username: str,
    password: str,
    window_start: datetime,
) -> list[str]:
    """Run synchronous IMAP fetch in thread pool; return list of In-Reply-To values."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _EXECUTOR,
        _sync_fetch_reply_tos,
        imap_host,
        username,
        password,
        window_start,
    )


def _sync_fetch_reply_tos(
    imap_host: str,
    username: str,
    password: str,
    window_start: datetime,
) -> list[str]:
    """Synchronous — runs in thread executor."""
    try:
        mail = imaplib.IMAP4_SSL(imap_host, timeout=10)
    except Exception as exc:
        logger.debug("imap_connect_failed", host=imap_host, reason=str(exc))
        return []

    reply_tos: list[str] = []
    try:
        mail.login(username, password)
        mail.select("INBOX", readonly=True)

        since_str = window_start.strftime("%d-%b-%Y")
        _status, msg_nums = mail.search(None, f"SINCE {since_str}")
        if _status != "OK" or not msg_nums[0]:
            return []

        ids = msg_nums[0].split()[-_BATCH_LIMIT:]
        for num in ids:
            try:
                _s, data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (IN-REPLY-TO)])")
                if not data or not data[0]:
                    continue
                raw = data[0][1] if isinstance(data[0], tuple) else data[0]
                msg = email.message_from_bytes(raw)
                irt = (msg.get("In-Reply-To") or "").strip().strip("<>")
                if irt:
                    reply_tos.append(irt)
            except Exception as exc:
                logger.debug("imap_fetch_error", reason=str(exc))
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    return reply_tos
