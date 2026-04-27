"""Finance source seeder — pre-populates ScrapingSource with finance-industry URLs.

Run once on startup or via CLI: `python -m app.tasks.finance_source_seeder`
Also registered as a Celery task for on-demand re-seeding.
"""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

# Finance-specific scraping sources
FINANCE_SOURCES = [
    # SEC EDGAR — public company filings with executive contacts
    {
        "name": "SEC EDGAR Company Search",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=&dateb=&owner=include&count=100&search_text=",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    {
        "name": "SEC EDGAR Investment Advisers",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&State=0&SIC=6282&dateb=&owner=include&count=100&search_text=",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    # CFA Institute
    {
        "name": "CFA Institute Member Directory",
        "url": "https://www.cfainstitute.org/en/membership/find-a-member",
        "source_type": "directory",
        "scraper_engine": "playwright",
    },
    {
        "name": "CFA Society New York",
        "url": "https://cfany.org/about/leadership/",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    # Industry associations
    {
        "name": "SIFMA Member Directory",
        "url": "https://www.sifma.org/about/members/",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    {
        "name": "AIMA Member Directory",
        "url": "https://www.aima.org/membership/member-directory.html",
        "source_type": "directory",
        "scraper_engine": "playwright",
    },
    {
        "name": "MFA Member Directory",
        "url": "https://www.managedfunds.org/members/",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    {
        "name": "NVCA Member Directory",
        "url": "https://nvca.org/members/",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    {
        "name": "ILPA Member Directory",
        "url": "https://ilpa.org/members/",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    # Fund databases
    {
        "name": "Preqin Hedge Fund Database",
        "url": "https://www.preqin.com/data/hedge-funds",
        "source_type": "directory",
        "scraper_engine": "playwright",
    },
    {
        "name": "Hedgeco Fund Directory",
        "url": "https://www.hedgeco.net/hedgebase/search.php",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    # News / conference speaker lists
    {
        "name": "Bloomberg Markets Finance Events",
        "url": "https://www.bloomberg.com/live/events",
        "source_type": "news",
        "scraper_engine": "firecrawl",
    },
    {
        "name": "FT Future of Asset Management",
        "url": "https://live.ft.com/Events/2025/FT-Future-of-Asset-Management-US",
        "source_type": "directory",
        "scraper_engine": "firecrawl",
    },
    # LinkedIn search (structured queries, not direct scraping)
    {
        "name": "LinkedIn Finance Executive Search",
        "url": "https://www.linkedin.com/search/results/people/?keywords=hedge+fund+portfolio+manager&origin=GLOBAL_SEARCH_HEADER",
        "source_type": "social",
        "scraper_engine": "playwright",
    },
    {
        "name": "LinkedIn PE Managing Director",
        "url": "https://www.linkedin.com/search/results/people/?keywords=private+equity+managing+director+email&origin=GLOBAL_SEARCH_HEADER",
        "source_type": "social",
        "scraper_engine": "playwright",
    },
]


@celery_app.task(name="app.tasks.finance_source_seeder.seed_finance_sources", bind=True)
def seed_finance_sources(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_run())


async def _run() -> dict:
    from app.database import async_session_factory

    async with async_session_factory() as session:
        return await run_seeder(session)


async def run_seeder(session) -> dict:  # type: ignore[no-untyped-def]
    import uuid

    from sqlalchemy import select

    from app.models.scraping_source import ScrapingSource

    added = 0
    skipped = 0

    for src in FINANCE_SOURCES:
        exists = await session.execute(
            select(ScrapingSource).where(ScrapingSource.url == src["url"])
        )
        if exists.scalar_one_or_none():
            skipped += 1
            continue

        record = ScrapingSource(
            id=uuid.uuid4(),
            name=src["name"],
            url=src["url"],
            source_type=src["source_type"],
            audience_category="finance",
            is_active=True,
            scraper_engine=src["scraper_engine"],
        )
        session.add(record)
        added += 1

    await session.commit()
    logger.info("finance_sources_seeded", added=added, skipped=skipped)
    return {"added": added, "skipped": skipped, "total": len(FINANCE_SOURCES)}


if __name__ == "__main__":
    asyncio.run(_run())
