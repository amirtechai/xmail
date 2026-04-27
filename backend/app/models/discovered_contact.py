"""Discovered contact model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VerifiedStatus(str, Enum):
    UNVERIFIED = "unverified"
    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    CATCH_ALL = "catch_all"
    DISPOSABLE = "disposable"
    ROLE_BASED = "role_based"


class DiscoveredContact(Base):
    __tablename__ = "discovered_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # SHA256 of normalised email for fast dedup lookups
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    twitter_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    # search_query | rss | direct_url | social_handle
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="search_query")
    audience_type_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # ISO 3166-1 alpha-2
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    # BCP 47
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    verified_status: Mapped[str] = mapped_column(
        String(30), default=VerifiedStatus.UNVERIFIED.value, nullable=False, index=True
    )
    mx_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smtp_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_disposable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_role_based: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enrichment_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    times_suggested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        Index("ix_contact_audience_discovered", "audience_type_key", "discovered_at"),
        Index("ix_contact_verified_score", "verified_status", "confidence_score"),
    )
