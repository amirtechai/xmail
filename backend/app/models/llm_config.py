"""LLM provider configuration model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMProvider(str, Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ZAI = "zai"
    GROQ = "groq"
    CUSTOM = "custom"


class LLMConfiguration(Base):
    __tablename__ = "llm_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    selected_model: Mapped[str] = mapped_column(String(255), nullable=False)
    # purpose: planner, extractor, draft_writer, judge, default
    purpose: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_llm_config_user_default", "user_id", "is_default"),
        Index("ix_llm_config_user_purpose", "user_id", "purpose"),
    )
