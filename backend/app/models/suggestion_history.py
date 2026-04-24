"""Suggestion history — prevents same contact being suggested twice."""

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED_FOR_CAMPAIGN = "accepted_for_campaign"
    REJECTED = "rejected"
    SENT = "sent"


class SuggestionHistory(Base):
    __tablename__ = "suggestion_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    list_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default=SuggestionStatus.PENDING.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        # Each contact appears only once across all suggestion history
        UniqueConstraint("contact_id", name="uq_suggestion_contact_once"),
        Index("ix_suggestion_date_status", "list_date", "status"),
    )
