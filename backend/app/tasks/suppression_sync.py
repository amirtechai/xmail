"""Suppression list sync task — runs every 15 minutes.

Ensures bloom filter stays in sync with DB suppression list.
"""

import asyncio

from app.tasks.celery_app import celery_app

from app.core.logger import get_logger
logger = get_logger(__name__)


@celery_app.task(name="app.tasks.suppression_sync.sync_suppression_list", bind=True)
def sync_suppression_list(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_sync())


async def _sync() -> dict:
    from app.database import async_session_factory, get_redis
    from app.deduplication.bloom_filter import bf_add_batch
    from app.deduplication.hasher import hash_email
    from app.models.suppression_list import SuppressionList
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(select(SuppressionList.email))
        emails = [r[0] for r in result.fetchall()]

    if not emails:
        return {"synced": 0}

    hashes = [hash_email(e) for e in emails]
    redis = await get_redis()
    try:
        await bf_add_batch(redis, hashes)
    finally:
        await redis.aclose()

    logger.info("suppression_sync_done", count=len(hashes))
    return {"synced": len(hashes)}
