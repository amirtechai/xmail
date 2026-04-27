"""Suppression list schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.suppression_list import SuppressionReason


class SuppressionOut(BaseModel):
    id: str  # UUID serialised as str
    email: str
    reason: str
    notes: str | None
    added_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):  # type: ignore[override]
        # Coerce UUID id to str before Pydantic sees it
        if hasattr(obj, "__dict__"):
            import uuid as _uuid

            raw_id = getattr(obj, "id", None)
            if isinstance(raw_id, _uuid.UUID):
                obj.__dict__["id"] = str(raw_id)
        return super().model_validate(obj, **kwargs)


class SuppressionAddRequest(BaseModel):
    email: EmailStr
    reason: SuppressionReason
    notes: str | None = None


class SuppressionListResponse(BaseModel):
    items: list[SuppressionOut]
    total: int
    page: int
    page_size: int
