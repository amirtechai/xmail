"""Campaign schemas."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    target_audience_keys: list[str] = []
    target_countries: list[str] = []
    min_confidence: int = 50
    smtp_config_id: str | None = None
    llm_config_id: str | None = None
    email_subject: str = ""
    email_subject_b: str | None = None  # A/B variant
    email_body_html: str = ""
    email_body_text: str = ""
    legitimate_interest_reason: str = ""
    scheduled_at: datetime | None = None
    batch_size_per_hour: int | None = None
    dry_run: bool = False


class CampaignOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    target_audience_keys: list[str]
    smtp_config_id: str | None
    llm_config_id: str | None
    email_subject: str
    email_subject_b: str | None
    email_body_html: str
    email_body_text: str
    legitimate_interest_reason: str
    scheduled_at: str | None
    batch_size_per_hour: int | None
    dry_run: bool
    created_at: str


class AIDraftRequest(BaseModel):
    audience_key: str
    product_context: str
    tone: str = "professional"  # professional | friendly | formal
    language: str = "en"
    llm_config_id: str | None = None

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        allowed = {"professional", "friendly", "formal", "concise"}
        if v not in allowed:
            raise ValueError(f"tone must be one of {allowed}")
        return v


class AIDraftResponse(BaseModel):
    subject: str
    body_html: str
    body_text: str
    subject_variants: list[str]


class TestSendRequest(BaseModel):
    to_email: str
    subject_override: str | None = None


class SendRequest(BaseModel):
    legitimate_interest_reason: str
    scheduled_at: datetime | None = None
    batch_size_per_hour: int | None = None


class SequenceCreate(BaseModel):
    name: str = "Follow-up sequence"
    is_active: bool = True
    stop_on_reply: bool = True


class SequenceUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    stop_on_reply: bool | None = None


class SequenceStepCreate(BaseModel):
    step_number: int
    delay_days: int = 3
    email_subject: str
    email_body_html: str = ""
    email_body_text: str = ""


class SequenceStepUpdate(BaseModel):
    delay_days: int | None = None
    email_subject: str | None = None
    email_body_html: str | None = None
    email_body_text: str | None = None
