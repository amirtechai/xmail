"""Search web node — executes search queries via SerpAPI, Firecrawl, or DuckDuckGo."""

import httpx

from app.agents.state import XmailState
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_DDG_API = "https://api.duckduckgo.com/"
_SERP_API = "https://serpapi.com/search"
_MAX_URLS_PER_QUERY = 10


async def _serp_search(query: str, api_key: str) -> list[str]:
    """Google search via SerpAPI — best quality results."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            _SERP_API,
            params={
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": str(_MAX_URLS_PER_QUERY),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [r["link"] for r in data.get("organic_results", []) if r.get("link")]


async def _firecrawl_search(query: str, api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.firecrawl.dev/v1/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": query, "limit": _MAX_URLS_PER_QUERY},
        )
        resp.raise_for_status()
        data = resp.json()
        return [r["url"] for r in data.get("data", []) if r.get("url")]


async def _ddg_search(query: str) -> list[str]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            _DDG_API,
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers={"User-Agent": "Xmail/1.0 (research bot)"},
        )
        resp.raise_for_status()
        data = resp.json()
        urls = [r["FirstURL"] for r in data.get("RelatedTopics", []) if r.get("FirstURL")]
        return urls[:_MAX_URLS_PER_QUERY]


async def search_web_node(state: XmailState) -> dict:
    queries = state.get("search_queries", [])
    collected: list[str] = list(state.get("raw_urls", []))
    seen: set[str] = set(collected)

    for query in queries:
        try:
            if settings.serpapi_api_key:
                urls = await _serp_search(query, settings.serpapi_api_key)
            elif settings.firecrawl_api_key:
                urls = await _firecrawl_search(query, settings.firecrawl_api_key)
            else:
                urls = await _ddg_search(query)
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    collected.append(url)
        except Exception as exc:
            logger.warning("search_query_failed", query=query[:80], reason=str(exc))

    logger.info("search_web_done", url_count=len(collected))
    return {"raw_urls": collected}
