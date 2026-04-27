"""Stale verification cleanup — weekly Monday 02:00 UTC.

Removes unverified contacts older than 90 days and resets
'risky' contacts for re-verification after 30 days.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

UNVERIFIED_TTL_DAYS = 90
RISKY_REVERIFY_DAYS = 30


@celery_app.task(name="app.tasks.stale_verification_cleanup.cleanup_stale_verifications", bind=True)
def cleanup_stale_verifications(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_cleanup())


async def _cleanup() -> dict:
    from sqlalchemy import delete, update

    from app.database import async_session_factory
    from app.models.discovered_contact import DiscoveredContact, VerifiedStatus

    now = datetime.now(UTC)
    unverified_cutoff = now - timedelta(days=UNVERIFIED_TTL_DAYS)
    risky_cutoff = now - timedelta(days=RISKY_REVERIFY_DAYS)

    async with async_session_factory() as session:
        # Delete old unverified contacts
        del_result = await session.execute(
            delete(DiscoveredContact).where(
                DiscoveredContact.verified_status == VerifiedStatus.UNVERIFIED,
                DiscoveredContact.created_at < unverified_cutoff,
            )
        )
        deleted = del_result.rowcount

        # Reset risky to unverified for re-check
        upd_result = await session.execute(
            update(DiscoveredContact)
            .where(
                DiscoveredContact.verified_status == VerifiedStatus.RISKY,
                DiscoveredContact.updated_at < risky_cutoff,
            )
            .values(verified_status=VerifiedStatus.UNVERIFIED)
        )
        reset = upd_result.rowcount

        await session.commit()

    logger.info("stale_cleanup_done", deleted=deleted, reset_to_unverified=reset)
    return {"deleted": deleted, "reset_to_unverified": reset}
