"""Daily summary report model."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    contacts_discovered: Mapped[int] = mapped_column(default=0, nullable=False)
    contacts_verified: Mapped[int] = mapped_column(default=0, nullable=False)
    emails_sent: Mapped[int] = mapped_column(default=0, nullable=False)
    emails_delivered: Mapped[int] = mapped_column(default=0, nullable=False)
    emails_bounced: Mapped[int] = mapped_column(default=0, nullable=False)
    emails_opened: Mapped[int] = mapped_column(default=0, nullable=False)
    emails_clicked: Mapped[int] = mapped_column(default=0, nullable=False)
    unsubscribes: Mapped[int] = mapped_column(default=0, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("report_date", name="uq_daily_report_date"),)
