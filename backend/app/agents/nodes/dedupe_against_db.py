"""Dedup node — bloom filter fast-path + DB uniqueness guarantee."""

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)


async def _bloom_contains(email: str, redis_client) -> bool:  # type: ignore[no-untyped-def]
    """Check Redis bloom filter (BF.EXISTS). Returns False if bloom not configured."""
    try:
        return bool(await redis_client.execute_command("BF.EXISTS", "xmail:seen_emails", email))
    except Exception:
        return False


async def _bloom_add(email: str, redis_client) -> None:  # type: ignore[no-untyped-def]
    try:
        await redis_client.execute_command("BF.ADD", "xmail:seen_emails", email)
    except Exception:
        pass


async def _db_contains(email: str, session) -> bool:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from app.models.discovered_contact import DiscoveredContact
    from app.models.suppression_list import SuppressionList

    # Check suppression list first (hard block)
    suppressed = await session.execute(
        select(SuppressionList).where(SuppressionList.email == email)
    )
    if suppressed.scalar_one_or_none():
        return True

    # Check if already discovered/processed
    existing = await session.execute(
        select(DiscoveredContact).where(DiscoveredContact.email == email)
    )
    return existing.scalar_one_or_none() is not None


async def dedupe_against_db_node(state: XmailState, session, redis_client) -> dict:  # type: ignore[no-untyped-def]
    contacts = state.get("validated_contacts", [])
    unique: list[dict] = []

    for contact in contacts:
        email = contact.get("email", "").lower()
        if not email:
            continue
        # Fast path: bloom filter
        if await _bloom_contains(email, redis_client):
            continue
        # Authoritative: DB check
        if await _db_contains(email, session):
            await _bloom_add(email, redis_client)  # back-fill bloom
            continue
        # New contact — add to bloom and keep
        await _bloom_add(email, redis_client)
        unique.append(contact)

    logger.info("dedup_done", input=len(contacts), unique=len(unique))
    return {"deduplicated_contacts": unique}
