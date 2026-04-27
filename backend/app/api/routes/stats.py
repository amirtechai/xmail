"""Dashboard statistics endpoint."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models.daily_report import DailyReport
from app.models.discovered_contact import DiscoveredContact
from app.models.suppression_list import SuppressionList

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
async def dashboard_stats(session: SessionDep, _: CurrentUser) -> dict:
    today = date.today()
    today_dt = datetime.combine(today, datetime.min.time())
    week_dt = datetime.combine(today - timedelta(days=7), datetime.min.time())
    month_ago = today - timedelta(days=30)

    contacts_today = (
        await session.execute(
            select(func.count())
            .select_from(DiscoveredContact)
            .where(DiscoveredContact.discovered_at >= today_dt)
        )
    ).scalar_one()

    contacts_week = (
        await session.execute(
            select(func.count())
            .select_from(DiscoveredContact)
            .where(DiscoveredContact.discovered_at >= week_dt)
        )
    ).scalar_one()

    contacts_total = (
        await session.execute(select(func.count()).select_from(DiscoveredContact))
    ).scalar_one()

    verified_total = (
        await session.execute(
            select(func.count())
            .select_from(DiscoveredContact)
            .where(DiscoveredContact.verified_status.in_(["valid", "risky"]))
        )
    ).scalar_one()

    suppression_total = (
        await session.execute(select(func.count()).select_from(SuppressionList))
    ).scalar_one()

    # 30-day trend from DailyReport
    trend_rows = (
        (
            await session.execute(
                select(DailyReport)
                .where(DailyReport.report_date >= month_ago)
                .order_by(DailyReport.report_date.asc())
            )
        )
        .scalars()
        .all()
    )
    trend = [
        {
            "date": str(r.report_date),
            "contacts": r.contacts_discovered,
            "sent": r.emails_sent,
            "opened": r.emails_opened,
        }
        for r in trend_rows
    ]

    # Top 10 domains by contact count (PostgreSQL split_part)
    domain_rows = (
        await session.execute(
            select(
                func.split_part(DiscoveredContact.email, "@", 2).label("domain"),
                func.count().label("cnt"),
            )
            .group_by("domain")
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    top_domains = [{"domain": r.domain, "count": r.cnt} for r in domain_rows]

    # Audience breakdown (top 12)
    audience_rows = (
        await session.execute(
            select(
                DiscoveredContact.audience_type_key.label("key"),
                func.count().label("cnt"),
            )
            .group_by(DiscoveredContact.audience_type_key)
            .order_by(func.count().desc())
            .limit(12)
        )
    ).all()
    audience_breakdown = [{"key": r.key, "count": r.cnt} for r in audience_rows]

    return {
        "contacts_today": contacts_today,
        "contacts_week": contacts_week,
        "contacts_total": contacts_total,
        "verified_total": verified_total,
        "suppression_total": suppression_total,
        "trend": trend,
        "top_domains": top_domains,
        "audience_breakdown": audience_breakdown,
    }
