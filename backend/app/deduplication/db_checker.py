"""Authoritative DB check for exact email deduplication."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deduplication.hasher import hash_email
from app.models.discovered_contact import DiscoveredContact
from app.models.suppression_list import SuppressionList


async def is_suppressed(session: AsyncSession, email: str) -> bool:
    """True if email is in suppression list (unsubscribed, bounced, complained, etc.)."""
    result = await session.execute(
        select(SuppressionList.id).where(SuppressionList.email == email.lower().strip()).limit(1)
    )
    return result.scalar() is not None


async def is_already_discovered(session: AsyncSession, email: str) -> bool:
    """True if email hash is already in discovered_contacts."""
    email_hash = hash_email(email)
    result = await session.execute(
        select(DiscoveredContact.id).where(DiscoveredContact.email_hash == email_hash).limit(1)
    )
    return result.scalar() is not None


async def is_duplicate(session: AsyncSession, email: str) -> tuple[bool, str]:
    """Check both tables. Returns (is_dup, reason)."""
    if await is_suppressed(session, email):
        return True, "suppressed"
    if await is_already_discovered(session, email):
        return True, "already_discovered"
    return False, ""


async def load_all_hashes(session: AsyncSession) -> list[str]:
    """Load all email hashes from discovered_contacts for bloom warmup."""
    result = await session.execute(
        select(DiscoveredContact.email_hash).where(DiscoveredContact.email_hash.is_not(None))
    )
    return [row[0] for row in result.fetchall()]
