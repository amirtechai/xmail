"""LangGraph shared state definition for the Xmail discovery pipeline."""

from typing import Annotated, Any, NotRequired

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class XmailState(TypedDict):
    # Input
    campaign_id: str
    audience_type: str
    audience_keywords: list[str]
    target_count: int
    industry_vertical: NotRequired[str]  # e.g. "finance", "tech", "healthcare"

    # Pipeline progress
    search_queries: list[str]
    raw_urls: list[str]
    crawled_pages: list[dict]          # [{url, html, text}]
    extracted_emails: list[str]
    enriched_contacts: list[dict]      # [{email, name, company, title, ...}]
    validated_contacts: list[dict]     # [{email, status, score, ...}]
    deduplicated_contacts: list[dict]
    inferred_emails: list[str]      # emails generated via domain pattern inference
    persisted_count: int

    # Control
    error: str | None
    retry_count: int
    max_retries: int

    # LangGraph messages for tool-calling nodes
    messages: Annotated[list[Any], add_messages]
