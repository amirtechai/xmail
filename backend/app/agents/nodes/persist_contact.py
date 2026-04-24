"""Persist contact node — saves deduplicated contacts to DB with email_hash."""

import hashlib
import uuid

from app.agents.state import XmailState
from app.core.logger import get_logger
from app.models.discovered_contact import DiscoveredContact

logger = get_logger(__name__)


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


async def persist_contact_node(state: XmailState, session) -> dict:  # type: ignore[no-untyped-def]
    contacts = state.get("deduplicated_contacts", [])
    campaign_id = state.get("campaign_id")
    saved = 0

    for contact in contacts:
        email = contact.get("email", "").lower()
        if not email:
            continue
        record = DiscoveredContact(
            id=uuid.uuid4(),
            campaign_id=uuid.UUID(campaign_id) if campaign_id else None,
            email=email,
            email_hash=_email_hash(email),
            name=contact.get("name"),
            company=contact.get("company"),
            title=contact.get("title"),
            linkedin_url=contact.get("linkedin_url"),
            verified_status=contact.get("verified_status", "unverified"),
            confidence_score=contact.get("confidence_score", 0),
            source_url=contact.get("source_url"),
        )
        session.add(record)
        saved += 1

    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error("persist_failed", error=str(exc))
        return {"persisted_count": 0, "error": str(exc)}

    logger.info("persist_done", saved=saved)
    return {"persisted_count": saved}
