"""Campaign model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SEARCHING = "searching"
    READY_TO_SEND = "ready_to_send"
    SENDING = "sending"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default=CampaignStatus.DRAFT.value, nullable=False, index=True
    )
    # List of audience type keys
    target_audience_type_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    llm_config_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    smtp_config_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    email_subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email_body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email_body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachments_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    logo_position: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # MANDATORY Legitimate Interest Assessment reason
    legitimate_interest_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    # Max emails sent per hour (0 = unlimited)
    hourly_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_campaign_user_status", "user_id", "status"),)
