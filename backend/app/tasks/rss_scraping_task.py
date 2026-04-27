"""Daily RSS feed refresh task.

Parses all active NEWS-type ScrapingSource entries, updates last_scraped_at,
and returns a summary. The actual URL injection into discovery pipelines
happens via rss_feed_reader_node inside the LangGraph pipeline.
"""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

_MAX_ENTRIES_PER_FEED = 50


@celery_app.task(
    name="app.tasks.rss_scraping_task.refresh_rss_feeds",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def refresh_rss_feeds(self) -> dict:  # type: ignore[override]
    try:
        return asyncio.get_event_loop().run_until_complete(_refresh())
    except Exception as exc:
        logger.error("rss_refresh_failed", reason=str(exc))
        raise self.retry(exc=exc) from exc


async def _refresh() -> dict:
    from datetime import datetime

    import feedparser
    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.scraping_source import ScrapingSource, SourceType

    total_entries = 0
    feeds_ok = 0
    feeds_error = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(ScrapingSource).where(
                ScrapingSource.is_active.is_(True),
                ScrapingSource.source_type == SourceType.NEWS.value,
            )
        )
        sources = result.scalars().all()

        if not sources:
            logger.info("rss_refresh_skipped", reason="no_active_sources")
            return {"feeds_ok": 0, "feeds_error": 0, "total_entries": 0}

        loop = asyncio.get_event_loop()
        for source in sources:
            try:
                feed = await loop.run_in_executor(None, feedparser.parse, source.url)
                count = min(len(feed.entries), _MAX_ENTRIES_PER_FEED)
                total_entries += count
                source.last_scraped_at = datetime.utcnow()
                feeds_ok += 1
                logger.debug("rss_refreshed", source=source.name, entries=count)
            except Exception as exc:
                feeds_error += 1
                logger.warning("rss_refresh_error", source=source.url, reason=str(exc))

        if feeds_ok:
            await session.commit()

    logger.info(
        "rss_refresh_done", feeds_ok=feeds_ok, feeds_error=feeds_error, entries=total_entries
    )
    return {"feeds_ok": feeds_ok, "feeds_error": feeds_error, "total_entries": total_entries}
