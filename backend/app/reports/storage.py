"""Report file storage — local filesystem with optional S3/R2 upload."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)

# Reports stored under /var/xmail/reports/<YYYY>/<MM>/<DD>/
_BASE_DIR = Path("/var/xmail/reports")
RETENTION_DAYS = 90


def report_dir(report_date: date) -> Path:
    return _BASE_DIR / str(report_date.year) / f"{report_date.month:02d}" / f"{report_date.day:02d}"


def pdf_path(report_date: date) -> Path:
    return report_dir(report_date) / f"xmail_report_{report_date.isoformat()}.pdf"


def xml_path(report_date: date) -> Path:
    return report_dir(report_date) / f"xmail_report_{report_date.isoformat()}.xml"


def list_reports(limit: int = 90) -> list[dict]:
    """Return list of available reports, newest first."""
    reports: list[dict] = []
    if not _BASE_DIR.exists():
        return reports

    for pdf in sorted(_BASE_DIR.rglob("*.pdf"), reverse=True)[:limit]:
        xml = pdf.with_suffix(".xml")
        reports.append(
            {
                "date": pdf.stem.replace("xmail_report_", ""),
                "pdf_path": str(pdf),
                "xml_path": str(xml) if xml.exists() else None,
                "pdf_size": pdf.stat().st_size if pdf.exists() else 0,
            }
        )
    return reports


def cleanup_old_reports() -> int:
    """Delete reports older than RETENTION_DAYS. Returns count deleted."""
    if not _BASE_DIR.exists():
        return 0

    cutoff = datetime.now(UTC).date() - timedelta(days=RETENTION_DAYS)
    deleted = 0
    for f in _BASE_DIR.rglob("xmail_report_*.pdf"):
        try:
            report_date = date.fromisoformat(f.stem.replace("xmail_report_", ""))
            if report_date < cutoff:
                f.unlink(missing_ok=True)
                xml = f.with_suffix(".xml")
                xml.unlink(missing_ok=True)
                deleted += 1
        except (ValueError, OSError):
            pass

    logger.info("report_cleanup_done", deleted=deleted)
    return deleted
