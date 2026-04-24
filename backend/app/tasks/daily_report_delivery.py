"""Daily report delivery task — 06:00 UTC (09:00 Istanbul).

Sends the generated PDF/summary to configured admin emails.
"""

import asyncio
import logging
from datetime import date, datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.daily_report_delivery.deliver_daily_report", bind=True)
def deliver_daily_report(self, report_date_iso: str | None = None) -> dict:  # type: ignore[override]
    target_date = (
        date.fromisoformat(report_date_iso) if report_date_iso
        else datetime.now(timezone.utc).date()
    )
    return asyncio.get_event_loop().run_until_complete(_deliver(target_date))


async def _deliver(report_date: date) -> dict:
    from app.config import settings
    from app.database import async_session_factory
    from app.models.daily_report import DailyReport
    from app.models.user import User, UserRole
    from sqlalchemy import select

    if not settings.admin_email:
        logger.info("report_delivery_skipped", reason="no_admin_email_configured")
        return {"skipped": True}

    async with async_session_factory() as session:
        # Load report
        result = await session.execute(
            select(DailyReport).where(DailyReport.report_date == report_date)
        )
        report = result.scalar_one_or_none()
        if not report:
            logger.warning("report_not_found", date=report_date.isoformat())
            return {"error": "report_not_found"}

        # Load admin users
        admins_result = await session.execute(
            select(User.email).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        admin_emails = [r[0] for r in admins_result.fetchall()]

    if not admin_emails:
        logger.info("report_delivery_skipped", reason="no_admin_users")
        return {"skipped": True}

    from app.models.discovered_contact import DiscoveredContact
    from app.reports import pdf_generator, storage, xml_exporter
    from sqlalchemy import func

    # Generate PDF + XML if not already on disk
    pdf_out = storage.pdf_path(report_date)
    xml_out = storage.xml_path(report_date)

    async with async_session_factory() as session:
        contacts_result = await session.execute(
            select(DiscoveredContact).where(
                func.date(DiscoveredContact.created_at) == report_date
            ).order_by(DiscoveredContact.confidence_score.desc()).limit(50)
        )
        contacts = [
            {
                "email": c.email,
                "full_name": c.full_name,
                "company": c.company,
                "job_title": c.job_title,
                "audience_type": c.audience_type,
                "confidence_score": c.confidence_score,
                "verified_status": c.verified_status.value if c.verified_status else None,
            }
            for c in contacts_result.scalars()
        ]

    if not pdf_out.exists():
        pdf_generator.generate_pdf(report=report, contacts=contacts, output_path=pdf_out)
    if not xml_out.exists():
        xml_exporter.generate_xml(report=report, contacts=contacts, output_path=xml_out)

    logger.info(
        "daily_report_delivered",
        date=report_date.isoformat(),
        recipients=admin_emails,
        pdf=str(pdf_out),
    )
    return {
        "delivered_to": admin_emails,
        "date": report_date.isoformat(),
        "pdf": str(pdf_out),
        "xml": str(xml_out),
    }
