"""Daily report delivery task — 06:00 UTC (09:00 Istanbul).

Sends the generated PDF/summary to configured admin emails.
"""

import asyncio
from datetime import UTC, date, datetime

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.daily_report_delivery.deliver_daily_report", bind=True)
def deliver_daily_report(self, report_date_iso: str | None = None) -> dict:  # type: ignore[override]
    target_date = (
        date.fromisoformat(report_date_iso) if report_date_iso else datetime.now(UTC).date()
    )
    return asyncio.get_event_loop().run_until_complete(_deliver(target_date))


async def _deliver(report_date: date) -> dict:
    from sqlalchemy import select

    from app.config import settings
    from app.database import async_session_factory
    from app.models.daily_report import DailyReport
    from app.models.user import User, UserRole

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

    from sqlalchemy import func

    from app.models.discovered_contact import DiscoveredContact
    from app.reports import pdf_generator, storage, xml_exporter

    # Generate PDF + XML if not already on disk
    pdf_out = storage.pdf_path(report_date)
    xml_out = storage.xml_path(report_date)

    async with async_session_factory() as session:
        contacts_result = await session.execute(
            select(DiscoveredContact)
            .where(func.date(DiscoveredContact.discovered_at) == report_date)
            .order_by(DiscoveredContact.confidence_score.desc())
            .limit(50)
        )
        contacts = [
            {
                "email": c.email,
                "full_name": c.full_name,
                "company": c.company,
                "job_title": c.title,
                "audience_type": c.audience_type_key,
                "confidence_score": c.confidence_score,
                "verified_status": c.verified_status,
            }
            for c in contacts_result.scalars()
        ]

    if not pdf_out.exists():
        pdf_generator.generate_pdf(report=report, contacts=contacts, output_path=pdf_out)
    if not xml_out.exists():
        xml_exporter.generate_xml(report=report, contacts=contacts, output_path=xml_out)

    # Load first active SMTP config to send the digest
    from app.models.smtp_config import SMTPConfiguration
    from app.sender.smtp_client import SMTPClient

    async with async_session_factory() as session:
        smtp_result = await session.execute(select(SMTPConfiguration).limit(1))
        smtp = smtp_result.scalar_one_or_none()

    if not smtp:
        logger.warning("report_delivery_skipped", reason="no_smtp_config")
        return {"skipped": True, "reason": "no_smtp_config"}

    open_rate = (
        round(report.emails_opened / report.emails_sent * 100, 1) if report.emails_sent else 0.0
    )
    click_rate = (
        round(report.emails_clicked / report.emails_sent * 100, 1) if report.emails_sent else 0.0
    )

    html_body = f"""
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#0f0f0f;color:#d4d4d4;padding:2rem;margin:0;">
<div style="max-width:560px;margin:0 auto;background:#1a1a1a;border:1px solid #2a2a2a;
border-radius:8px;padding:2rem;">
  <h2 style="color:#e5e5e5;margin:0 0 0.25rem;">Daily Report</h2>
  <p style="color:#666;margin:0 0 1.5rem;font-size:0.875rem;">{report_date.isoformat()}</p>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:0.5rem 0;color:#888;font-size:0.875rem;">Contacts Discovered</td>
        <td style="padding:0.5rem 0;text-align:right;color:#e5e5e5;font-weight:600;">{report.contacts_discovered}</td></tr>
    <tr><td style="padding:0.5rem 0;color:#888;font-size:0.875rem;border-top:1px solid #2a2a2a;">Emails Sent</td>
        <td style="padding:0.5rem 0;text-align:right;color:#e5e5e5;font-weight:600;border-top:1px solid #2a2a2a;">{report.emails_sent}</td></tr>
    <tr><td style="padding:0.5rem 0;color:#888;font-size:0.875rem;">Emails Bounced</td>
        <td style="padding:0.5rem 0;text-align:right;color:#ef4444;font-weight:600;">{report.emails_bounced}</td></tr>
    <tr><td style="padding:0.5rem 0;color:#888;font-size:0.875rem;">Open Rate</td>
        <td style="padding:0.5rem 0;text-align:right;color:#4ade80;font-weight:600;">{open_rate}%</td></tr>
    <tr><td style="padding:0.5rem 0;color:#888;font-size:0.875rem;">Click Rate</td>
        <td style="padding:0.5rem 0;text-align:right;color:#60a5fa;font-weight:600;">{click_rate}%</td></tr>
  </table>
</div>
</body></html>"""

    text_body = (
        f"Daily Report — {report_date.isoformat()}\n\n"
        f"Contacts Discovered : {report.contacts_discovered}\n"
        f"Emails Sent         : {report.emails_sent}\n"
        f"Emails Bounced      : {report.emails_bounced}\n"
        f"Open Rate           : {open_rate}%\n"
        f"Click Rate          : {click_rate}%\n"
    )

    client = SMTPClient(smtp)
    sent_to: list[str] = []
    failed: list[str] = []
    for email in admin_emails:
        try:
            await client.send(
                to_email=email,
                subject=f"Xmail Daily Report — {report_date.isoformat()}",
                html_body=html_body,
                text_body=text_body,
                unsubscribe_token="",
            )
            sent_to.append(email)
        except Exception as exc:
            logger.warning("report_email_failed", recipient=email, reason=str(exc))
            failed.append(email)

    logger.info(
        "daily_report_delivered",
        date=report_date.isoformat(),
        sent_to=sent_to,
        failed=failed,
        pdf=str(pdf_out),
    )
    return {
        "delivered_to": sent_to,
        "failed": failed,
        "date": report_date.isoformat(),
        "pdf": str(pdf_out),
        "xml": str(xml_out),
    }
