"""Finalize node — emits run summary and triggers daily report update."""

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)


async def finalize_node(state: XmailState, session) -> dict:  # type: ignore[no-untyped-def]
    persisted = state.get("persisted_count", 0)
    extracted = len(state.get("extracted_emails", []))
    validated = len(state.get("validated_contacts", []))
    deduped = len(state.get("deduplicated_contacts", []))

    logger.info(
        "agent_run_complete",
        campaign_id=state.get("campaign_id"),
        audience=state.get("audience_type"),
        extracted=extracted,
        validated=validated,
        deduped=deduped,
        persisted=persisted,
    )

    # Bump daily report counters
    try:
        from datetime import date

        from sqlalchemy import select

        from app.models.daily_report import DailyReport

        today = date.today()
        result = await session.execute(
            select(DailyReport).where(DailyReport.report_date == today)
        )
        report = result.scalar_one_or_none()
        if not report:
            report = DailyReport(report_date=today)
            session.add(report)
        report.contacts_discovered = (report.contacts_discovered or 0) + persisted
        report.contacts_verified = (report.contacts_verified or 0) + validated
        await session.commit()
    except Exception as exc:
        logger.warning("daily_report_update_failed", reason=str(exc))

    return {}
