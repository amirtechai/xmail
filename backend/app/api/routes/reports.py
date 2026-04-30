"""Report management endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser, get_session
from app.models.daily_report import DailyReport
from app.models.discovered_contact import DiscoveredContact
from app.reports import pdf_generator, storage, xml_exporter
from app.schemas.report import ReportGenerateRequest, ReportListItem, ReportListResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=ReportListResponse)
async def list_reports(_: CurrentUser) -> ReportListResponse:
    items_raw = storage.list_reports(limit=90)
    items = [
        ReportListItem(
            date=r["date"],
            pdf_available=bool(r["pdf_path"] and Path(r["pdf_path"]).exists()),
            xml_available=bool(r["xml_path"] and Path(r["xml_path"]).exists()),
            pdf_size=r["pdf_size"],
        )
        for r in items_raw
    ]
    return ReportListResponse(items=items, total=len(items))


@router.post("/generate", status_code=202)
async def generate_report(
    body: ReportGenerateRequest,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger on-demand report generation for a specific date."""
    result = await session.execute(
        select(DailyReport).where(DailyReport.report_date == body.report_date)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail=f"No report data for {body.report_date}")

    from sqlalchemy import Date as SADate
    from sqlalchemy import cast

    contacts_result = await session.execute(
        select(DiscoveredContact)
        .where(cast(DiscoveredContact.discovered_at, SADate) == body.report_date)
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

    generated = []
    if body.format in ("pdf", "both"):
        pdf_generator.generate_pdf(
            report=report,
            contacts=contacts,
            output_path=storage.pdf_path(body.report_date),
        )
        generated.append("pdf")

    if body.format in ("xml", "both"):
        xml_exporter.generate_xml(
            report=report,
            contacts=contacts,
            output_path=storage.xml_path(body.report_date),
        )
        generated.append("xml")

    return {"generated": generated, "date": body.report_date.isoformat()}


@router.get("/download/{report_date}/pdf")
async def download_pdf(report_date: str, _: CurrentUser) -> FileResponse:
    from datetime import date

    try:
        d = date.fromisoformat(report_date)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        ) from None

    path = storage.pdf_path(d)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF report not found. Generate it first.")

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"xmail_report_{report_date}.pdf",
    )


@router.get("/download/{report_date}/xml")
async def download_xml(report_date: str, _: CurrentUser) -> FileResponse:
    from datetime import date

    try:
        d = date.fromisoformat(report_date)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        ) from None

    path = storage.xml_path(d)
    if not path.exists():
        raise HTTPException(status_code=404, detail="XML report not found. Generate it first.")

    return FileResponse(
        path=str(path),
        media_type="application/xml",
        filename=f"xmail_report_{report_date}.xml",
    )


@router.delete("/cleanup", status_code=200)
async def cleanup_old_reports(_: AdminUser) -> dict:
    """Manually trigger 90-day retention cleanup."""
    deleted = storage.cleanup_old_reports()
    return {"deleted": deleted}
