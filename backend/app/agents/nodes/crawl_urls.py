"""Crawl URLs node — fetches page content via Firecrawl with Playwright fallback."""

import asyncio

import httpx

from app.agents.state import XmailState
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_MAX_CONCURRENT = 5
_PAGE_TIMEOUT = 30


async def _fetch_firecrawl(url: str, api_key: str) -> dict | None:
    async with httpx.AsyncClient(timeout=_PAGE_TIMEOUT) as client:
        resp = await client.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"url": url, "formats": ["markdown", "html"]},
        )
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", {})
        return {"url": url, "html": data.get("html", ""), "text": data.get("markdown", "")}


async def _fetch_httpx(url: str) -> dict | None:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Xmail/1.0; research bot)"}
    async with httpx.AsyncClient(timeout=_PAGE_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        html = resp.text
        return {"url": url, "html": html, "text": html}


async def _crawl_single(url: str) -> dict | None:
    try:
        if settings.firecrawl_api_key:
            return await _fetch_firecrawl(url, settings.firecrawl_api_key)
        return await _fetch_httpx(url)
    except Exception as exc:
        logger.debug("crawl_failed", url=url[:80], error=str(exc))
        return None


async def crawl_urls_node(state: XmailState) -> dict:
    urls = state.get("raw_urls", [])
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def bounded(url: str) -> dict | None:
        async with semaphore:
            return await _crawl_single(url)

    results = await asyncio.gather(*[bounded(u) for u in urls])
    pages = [r for r in results if r]
    logger.info("crawl_done", pages=len(pages), attempted=len(urls))
    return {"crawled_pages": pages}
