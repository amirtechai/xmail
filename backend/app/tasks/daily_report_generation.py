"""Daily report generation task — 05:30 UTC."""

import asyncio
from datetime import date, datetime, timezone

from app.tasks.celery_app import celery_app

from app.core.logger import get_logger
logger = get_logger(__name__)


@celery_app.task(name="app.tasks.daily_report_generation.generate_daily_report", bind=True)
def generate_daily_report(self, report_date_iso: str | None = None) -> dict:  # type: ignore[override]
    target_date = (
        date.fromisoformat(report_date_iso) if report_date_iso
        else datetime.now(timezone.utc).date()
    )
    return asyncio.get_event_loop().run_until_complete(_generate(target_date))


async def _generate(report_date: date) -> dict:
    from app.database import async_session_factory
    from app.models.daily_report import DailyReport
    from app.models.discovered_contact import DiscoveredContact
    from app.models.sent_email import SentEmail, SentEmailStatus
    from sqlalchemy import func, select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with async_session_factory() as session:
        # Count discovered today
        discovered = await session.execute(
            select(func.count(DiscoveredContact.id)).where(
                func.date(DiscoveredContact.created_at) == report_date
            )
        )
        discovered_count = discovered.scalar_one()

        # Count emails sent today
        sent = await session.execute(
            select(func.count(SentEmail.id)).where(
                func.date(SentEmail.sent_at) == report_date,
                SentEmail.status == SentEmailStatus.SENT,
            )
        )
        sent_count = sent.scalar_one()

        # Count bounces today
        bounced = await session.execute(
            select(func.count(SentEmail.id)).where(
                func.date(SentEmail.sent_at) == report_date,
                SentEmail.status == SentEmailStatus.BOUNCED,
            )
        )
        bounced_count = bounced.scalar_one()

        # Upsert daily report
        stmt = pg_insert(DailyReport).values(
            report_date=report_date,
            contacts_discovered=discovered_count,
            emails_sent=sent_count,
            emails_bounced=bounced_count,
        ).on_conflict_do_update(
            index_elements=["report_date"],
            set_={
                "contacts_discovered": discovered_count,
                "emails_sent": sent_count,
                "emails_bounced": bounced_count,
            },
        )
        await session.execute(stmt)
        await session.commit()

    logger.info(
        "daily_report_generated",
        date=report_date.isoformat(),
        discovered=discovered_count,
        sent=sent_count,
        bounced=bounced_count,
    )
    return {
        "report_date": report_date.isoformat(),
        "contacts_discovered": discovered_count,
        "emails_sent": sent_count,
        "emails_bounced": bounced_count,
    }
