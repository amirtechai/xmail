"""Global suppression list — permanent blacklist for unsubscribed/bounced/complained."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SuppressionReason(str, Enum):
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    MANUAL = "manual"
    DO_NOT_CONTACT = "do_not_contact"


class SuppressionList(Base):
    __tablename__ = "suppression_list"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_suppression_reason_date", "reason", "added_at"),)
