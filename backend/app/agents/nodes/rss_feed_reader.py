"""RSS feed reader node — supplements raw_urls from active news sources.

Reads active NEWS-type ScrapingSource entries from DB, parses each feed with
feedparser (in a thread executor to avoid blocking), and appends article URLs
to raw_urls for the crawl_urls step.
"""

import asyncio
import logging
from datetime import datetime

from app.agents.state import XmailState

logger = logging.getLogger(__name__)

_MAX_ENTRIES_PER_FEED = 50


async def rss_feed_reader_node(state: XmailState, session) -> dict:  # type: ignore[no-untyped-def]
    import feedparser  # lazy: only loaded when the node runs
    from sqlalchemy import select

    from app.models.scraping_source import ScrapingSource, SourceType

    try:
        sources = (await session.execute(
            select(ScrapingSource).where(
                ScrapingSource.is_active.is_(True),
                ScrapingSource.source_type == SourceType.NEWS.value,
            )
        )).scalars().all()
    except Exception as exc:
        logger.warning("rss_db_error", error=str(exc))
        return {}

    if not sources:
        return {}

    loop = asyncio.get_event_loop()
    existing = set(state.get("raw_urls", []))
    new_urls: list[str] = []

    for source in sources:
        try:
            feed = await loop.run_in_executor(None, feedparser.parse, source.url)
            count = 0
            for entry in feed.entries[:_MAX_ENTRIES_PER_FEED]:
                url = entry.get("link") or entry.get("id") or ""
                if url and url not in existing:
                    new_urls.append(url)
                    existing.add(url)
                    count += 1
            source.last_scraped_at = datetime.utcnow()
            logger.debug("rss_parsed", source=source.name, entries=count)
        except Exception as exc:
            logger.warning("rss_parse_error", source=source.url, error=str(exc))

    if new_urls:
        await session.commit()
        logger.info("rss_urls_added", count=len(new_urls), feeds=len(sources))
        return {"raw_urls": list(existing)}

    return {}
