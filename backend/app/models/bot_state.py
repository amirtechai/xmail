"""Bot global state — singleton row (id always = 1)."""

from enum import Enum

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BotStateEnum(str, Enum):
    IDLE = "idle"
    DISCOVERING = "discovering"
    VERIFYING = "verifying"
    WAITING_APPROVAL = "waiting_approval"
    SENDING = "sending"
    PAUSED = "paused"
    ERROR = "error"


class BotState(Base):
    __tablename__ = "bot_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    state: Mapped[str] = mapped_column(
        String(30), default=BotStateEnum.IDLE.value, nullable=False
    )
    is_running: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_activity_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    daily_email_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_emails_sent: Mapped[int] = mapped_column(default=0, nullable=False)
