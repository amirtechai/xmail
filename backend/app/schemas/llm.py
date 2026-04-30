"""LLM configuration Pydantic schemas."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMConfigCreate(BaseModel):
    provider: str
    model_name: str = Field(..., min_length=1, max_length=255)
    api_key: str = Field(..., min_length=1)
    base_url: str | None = None
    is_default: bool = False
    purpose: str = "default"
    display_name: str | None = None


class LLMConfigOut(BaseModel):
    id: uuid.UUID
    provider: str
    model_name: str
    base_url: str | None
    is_active: bool
    purpose: str
    display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def remap(cls, v: Any) -> Any:
        # Map SQLAlchemy model attributes to schema fields
        if hasattr(v, "selected_model"):
            return {
                "id": v.id,
                "provider": v.provider,
                "model_name": v.selected_model,
                "base_url": v.base_url,
                "is_active": v.is_default,
                "purpose": v.purpose,
                "display_name": getattr(v, "display_name", None),
            }
        return v


class LLMTestRequest(BaseModel):
    prompt: str = Field(default="Say hello in one sentence.", max_length=500)


class LLMTestResponse(BaseModel):
    success: bool
    content: str | None = None
    error: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
