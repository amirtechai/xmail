"""Contact output + update schemas."""

from datetime import datetime

from pydantic import BaseModel


class ContactOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    first_name: str | None
    last_name: str | None
    job_title: str | None
    company: str | None
    website: str | None
    linkedin_url: str | None
    twitter_handle: str | None
    source_url: str
    source_type: str
    audience_type: str
    country: str | None
    language: str | None
    confidence_score: int
    relevance_score: float
    verified_status: str
    mx_valid: bool | None
    smtp_valid: bool | None
    is_disposable: bool
    is_role_based: bool
    created_at: str

    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    country: str | None = None
    language: str | None = None
    audience_type_key: str | None = None
    confidence_score: int | None = None


class BulkDeleteRequest(BaseModel):
    ids: list[str]


class ImportError(BaseModel):
    row: int
    email: str
    error: str


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[ImportError]


class VerifyBulkRequest(BaseModel):
    ids: list[str] | None = None  # None = re-verify all unverified contacts
