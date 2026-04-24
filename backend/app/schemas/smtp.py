"""SMTP configuration Pydantic schemas."""

import uuid

from pydantic import BaseModel, Field


class SMTPConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    use_tls: bool = True
    from_email: str = Field(..., min_length=5, max_length=255)
    from_name: str = Field(default="PriceONN Outreach", max_length=255)
    daily_send_limit: int = Field(default=500, ge=1, le=10000)
    is_default: bool = False


class SMTPConfigOut(BaseModel):
    id: uuid.UUID
    name: str
    host: str
    port: int
    username: str
    use_tls: bool
    from_email: str
    from_name: str | None
    is_default: bool
    daily_send_limit: int

    model_config = {"from_attributes": True}


class SMTPTestRequest(BaseModel):
    to_email: str
    subject: str = "Xmail SMTP Test"


class SMTPTestResponse(BaseModel):
    success: bool
    error: str | None = None
