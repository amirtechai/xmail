"""Target audience type model — 60 categories of financial industry contacts."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AudienceCategory(str, Enum):
    MARKETS = "markets"  # 10 — trading platforms, exchanges
    NEWS_MEDIA = "news_media"  # 10 — publications, newsletters, podcasts
    ANALYSIS = "analysis"  # 6  — signals, research, analytics
    INFLUENCERS = "influencers"  # 7  — social media, YouTube, Substack
    EDUCATION = "education"  # 5  — academies, courses, certifications
    BROKERS = "brokers"  # 9  — forex/stock/crypto brokers, IB, prime
    TOOLS = "tools"  # 5  — fintech SaaS, payment, regtech
    OTHER = "other"  # 8  — ecommerce, enterprise, global expansion


class TargetAudienceType(Base):
    __tablename__ = "target_audience_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    label_tr: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_enabled_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    icon_name: Mapped[str] = mapped_column(String(50), default="briefcase", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
