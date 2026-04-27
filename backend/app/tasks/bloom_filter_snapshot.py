"""Bloom filter snapshot — daily 03:00 UTC.

Rebuilds bloom filter from DB to prevent drift after restarts.
"""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.bloom_filter_snapshot.snapshot_bloom_filter", bind=True)
def snapshot_bloom_filter(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_snapshot())


async def _snapshot() -> dict:
    from sqlalchemy import select

    from app.database import async_session_factory, get_redis
    from app.deduplication.bloom_filter import BF_KEY, bf_initialize, bf_warmup
    from app.deduplication.db_checker import load_all_hashes
    from app.deduplication.hasher import hash_email
    from app.models.suppression_list import SuppressionList

    async with async_session_factory() as session:
        # Load all discovered hashes
        discovered_hashes = await load_all_hashes(session)

        # Load suppression list hashes
        result = await session.execute(select(SuppressionList.email))
        suppressed_hashes = [hash_email(r[0]) for r in result.fetchall()]

    all_hashes = list(set(discovered_hashes + suppressed_hashes))

    redis = await get_redis()
    try:
        # Delete and recreate bloom filter for clean state
        await redis.delete(BF_KEY)
        await bf_initialize(redis)
        loaded = await bf_warmup(redis, all_hashes)
    finally:
        await redis.aclose()

    logger.info("bloom_snapshot_done", total_hashes=loaded)
    return {"total_hashes": loaded}
