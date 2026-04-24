"""Bot campaign configuration — singleton row (id always = 1)."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BotConfig(Base):
    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Which audience type keys are enabled (empty = all enabled)
    enabled_audience_keys: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Targeting
    min_confidence: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    target_countries: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_languages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    exclude_domains: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # LLM provider to use (references llm_configurations.id)
    llm_config_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Schedule
    active_hours_start: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    active_hours_end: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    max_emails_per_day: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    max_emails_per_hour: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    run_on_weekends: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Behavior
    human_in_the_loop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
