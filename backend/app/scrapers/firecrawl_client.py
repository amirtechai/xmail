"""Firecrawl API client — search, scrape, and bulk crawl."""

import httpx

from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)
_BASE = "https://api.firecrawl.dev/v1"
_TIMEOUT = 60


class FirecrawlClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or settings.firecrawl_api_key

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/search",
                headers=self._headers,
                json={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def scrape(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/scrape",
                headers=self._headers,
                json={"url": url, "formats": ["markdown", "html"]},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def crawl(self, url: str, max_depth: int = 2, limit: int = 50) -> list[dict]:
        """Start crawl job and poll until complete."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            start = await client.post(
                f"{_BASE}/crawl",
                headers=self._headers,
                json={"url": url, "maxDepth": max_depth, "limit": limit},
            )
            start.raise_for_status()
            job_id = start.json().get("id")
            if not job_id:
                return []

            # Poll for completion
            import asyncio
            for _ in range(30):
                await asyncio.sleep(5)
                status = await client.get(f"{_BASE}/crawl/{job_id}", headers=self._headers)
                data = status.json()
                if data.get("status") == "completed":
                    return data.get("data", [])
                if data.get("status") == "failed":
                    logger.warning("firecrawl_crawl_failed", job_id=job_id)
                    return []

        return []
