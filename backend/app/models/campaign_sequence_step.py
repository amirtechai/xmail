"""A single step in a campaign follow-up sequence."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CampaignSequenceStep(Base):
    __tablename__ = "campaign_sequence_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # Step ordering within the sequence (1-based)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Days to wait after the previous step (or after initial send for step 1)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    email_subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email_body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email_body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_seq_step_sequence_number", "sequence_id", "step_number"),)
