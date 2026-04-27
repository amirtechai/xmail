"""Bounce processing task — runs every 30 minutes.

Reads SentEmail rows with BOUNCED status and adds them to suppression list.
"""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.bounce_processing.process_bounces", bind=True)
def process_bounces(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_process())


async def _process() -> dict:
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.database import async_session_factory
    from app.models.sent_email import SentEmail, SentEmailStatus
    from app.models.suppression_list import SuppressionList, SuppressionReason

    async with async_session_factory() as session:
        # Find bounced emails not yet suppressed
        bounced = await session.execute(
            select(SentEmail.recipient_email).where(
                SentEmail.status == SentEmailStatus.BOUNCED,
                SentEmail.bounce_processed.is_(False),
            )
        )
        bounce_emails = [r[0] for r in bounced.fetchall()]

        if not bounce_emails:
            return {"processed": 0}

        # Upsert into suppression list
        for email in bounce_emails:
            stmt = pg_insert(SuppressionList).values(
                email=email.lower().strip(),
                reason=SuppressionReason.BOUNCED,
                source="bounce_processor",
            ).on_conflict_do_nothing(index_elements=["email"])
            await session.execute(stmt)

        # Mark as processed
        from sqlalchemy import update
        await session.execute(
            update(SentEmail)
            .where(
                SentEmail.recipient_email.in_(bounce_emails),
                SentEmail.status == SentEmailStatus.BOUNCED,
            )
            .values(bounce_processed=True)
        )
        await session.commit()

    logger.info("bounce_processing_done", count=len(bounce_emails))
    return {"processed": len(bounce_emails)}
