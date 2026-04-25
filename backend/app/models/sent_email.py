"""Sent email tracking model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SentEmailStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"


class SentEmail(Base):
    __tablename__ = "sent_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    smtp_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    # SHA256 of body to detect template drift
    body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default=SentEmailStatus.QUEUED.value, nullable=False, index=True
    )
    bounce_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tracking_pixel_opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # [{url: str, timestamp: str}, ...]
    click_events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Set when this email is a follow-up sequence step (NULL = initial campaign send)
    sequence_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    # 'A' or 'B' when A/B testing is active; NULL otherwise
    ab_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)
    # Recipient address stored for bounce/suppression lookups
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Set to True once bounced address has been written to suppression list
    bounce_processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Webhook-reported timestamps (first occurrence only)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_sent_email_campaign_status", "campaign_id", "status"),)
