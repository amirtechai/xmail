"""Deduplication orchestrator: bloom filter fast-path + DB authoritative check."""

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.deduplication.bloom_filter import bf_add, bf_exists
from app.deduplication.db_checker import is_duplicate
from app.deduplication.hasher import hash_email


class DeduplicationResult:
    __slots__ = ("is_duplicate", "reason", "email_hash")

    def __init__(self, is_duplicate: bool, reason: str, email_hash: str) -> None:
        self.is_duplicate = is_duplicate
        self.reason = reason
        self.email_hash = email_hash


async def check_and_register(
    email: str,
    session: AsyncSession,
    redis: Redis,
) -> DeduplicationResult:
    """Check if email is a duplicate and register it if new.

    Flow:
    1. Bloom filter fast-path: if definitely NOT seen → skip DB check
    2. If possibly seen → authoritative DB check
    3. If new → add to bloom filter
    """
    email_hash = hash_email(email)

    maybe_seen = await bf_exists(redis, email_hash)

    if maybe_seen:
        dup, reason = await is_duplicate(session, email)
        if dup:
            return DeduplicationResult(True, reason, email_hash)

    # New email — register in bloom filter
    await bf_add(redis, email_hash)
    return DeduplicationResult(False, "", email_hash)


async def check_only(
    email: str,
    session: AsyncSession,
    redis: Redis,
) -> DeduplicationResult:
    """Check without registering (for dry-run / preview)."""
    email_hash = hash_email(email)
    maybe_seen = await bf_exists(redis, email_hash)
    if maybe_seen:
        dup, reason = await is_duplicate(session, email)
        return DeduplicationResult(dup, reason, email_hash)
    return DeduplicationResult(False, "", email_hash)
