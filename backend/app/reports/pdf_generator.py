"""Daily report PDF generator using ReportLab.

Produces a single-page A4 PDF with:
- Header with logo text + report date
- KPI summary table
- Discovered contacts detail table (top 50)
- Footer with generation timestamp
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand colours — Bloomberg dark theme adapted for print
_DARK = colors.HexColor("#0D1117")
_ACCENT = colors.HexColor("#F0B429")
_LIGHT_BG = colors.HexColor("#F5F5F5")
_BORDER = colors.HexColor("#CCCCCC")
_TEXT = colors.HexColor("#1A1A1A")
_MUTED = colors.HexColor("#666666")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=18,
            textColor=_DARK,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=_MUTED,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Heading2"],
            fontSize=11,
            textColor=_DARK,
            spaceBefore=12,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontSize=8,
            textColor=_MUTED,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontSize=8,
            textColor=_TEXT,
            alignment=TA_LEFT,
        ),
        "cell_right": ParagraphStyle(
            "cell_right",
            parent=base["Normal"],
            fontSize=8,
            textColor=_TEXT,
            alignment=TA_RIGHT,
        ),
    }


def _kpi_table(report: Any, styles: dict) -> Table:
    kpis = [
        ("Contacts Discovered", report.contacts_discovered),
        ("Contacts Verified", report.contacts_verified),
        ("Emails Sent", report.emails_sent),
        ("Emails Delivered", report.emails_delivered),
        ("Bounces", report.emails_bounced),
        ("Opens", report.emails_opened),
        ("Clicks", report.emails_clicked),
        ("Unsubscribes", report.unsubscribes),
    ]

    # Arrange in 2 columns
    rows = [["Metric", "Count", "Metric", "Count"]]
    for i in range(0, len(kpis), 2):
        left_k, left_v = kpis[i]
        right_k, right_v = kpis[i + 1] if i + 1 < len(kpis) else ("", "")
        rows.append([left_k, str(left_v), right_k, str(right_v)])

    col_widths = [6 * cm, 2.5 * cm, 6 * cm, 2.5 * cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_BG]),
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
                ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
            ]
        )
    )
    return t


def _contacts_table(contacts: list[dict], styles: dict) -> Table:
    headers = ["#", "Email", "Company", "Title", "Score", "Status", "Category"]
    rows = [headers]
    for i, c in enumerate(contacts[:50], 1):
        rows.append(
            [
                str(i),
                c.get("email", ""),
                (c.get("company") or "")[:30],
                (c.get("title") or "")[:25],
                str(c.get("confidence_score", "")),
                c.get("verified_status", ""),
                (c.get("audience_type") or "")[:20],
            ]
        )

    col_widths = [0.8 * cm, 5.5 * cm, 3.5 * cm, 3.5 * cm, 1.2 * cm, 2 * cm, 3 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_BG]),
                ("GRID", (0, 0), (-1, -1), 0.4, _BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (4, 1), (4, -1), "CENTER"),
            ]
        )
    )
    return t


def generate_pdf(
    report: Any,
    contacts: list[dict],
    output_path: Path | None = None,
) -> bytes:
    """Generate PDF report. Returns PDF bytes. Also writes to output_path if given."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = _styles()
    story = []

    # Header
    story.append(Paragraph("Xmail — Daily Outreach Report", styles["title"]))
    story.append(
        Paragraph(
            f"PriceONN.com &nbsp;|&nbsp; {report.report_date.strftime('%B %d, %Y')}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # KPI section
    story.append(Paragraph("Performance Summary", styles["section"]))
    story.append(_kpi_table(report, styles))
    story.append(Spacer(1, 0.5 * cm))

    # Contacts section
    if contacts:
        story.append(
            Paragraph(
                f"Discovered Contacts — {report.report_date.strftime('%Y-%m-%d')} "
                f"(showing up to 50 of {report.contacts_discovered})",
                styles["section"],
            )
        )
        story.append(_contacts_table(contacts, styles))

    # Footer
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Generated by Xmail &nbsp;|&nbsp; {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["footer"],
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)

    return pdf_bytes
