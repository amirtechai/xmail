"""Scraping source catalog model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SourceType(str, Enum):
    WEBSITE = "website"
    DIRECTORY = "directory"
    SOCIAL = "social"
    NEWS = "news"
    FORUM = "forum"
    API = "api"


class ScrapingSource(Base):
    __tablename__ = "scraping_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    audience_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Scrapy / Playwright / Firecrawl
    scraper_engine: Mapped[str] = mapped_column(String(20), default="firecrawl", nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    success_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
