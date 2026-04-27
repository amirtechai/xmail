"""LangGraph agent run tracking model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RunType(str, Enum):
    DISCOVERY = "discovery"
    VERIFICATION = "verification"
    ENRICHMENT = "enrichment"
    CAMPAIGN = "campaign"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=RunStatus.RUNNING.value, nullable=False, index=True
    )
    # LangGraph thread_id for crash recovery / resumption
    langgraph_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacts_discovered: Mapped[int] = mapped_column(default=0, nullable=False)
    emails_sent: Mapped[int] = mapped_column(default=0, nullable=False)
