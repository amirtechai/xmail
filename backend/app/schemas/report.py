"""Report schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class ReportListItem(BaseModel):
    date: str
    pdf_available: bool
    xml_available: bool
    pdf_size: int


class ReportListResponse(BaseModel):
    items: list[ReportListItem]
    total: int


class ReportGenerateRequest(BaseModel):
    report_date: date
    format: Literal["pdf", "xml", "both"] = "both"
