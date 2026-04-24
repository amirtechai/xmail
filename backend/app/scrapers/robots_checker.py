"""Robots.txt compliance checker with Redis caching."""

import urllib.robotparser
from urllib.parse import urlparse

import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)
_CACHE: dict[str, bool] = {}  # in-process cache; Redis used via caller
_BOT_NAME = "Xmailbot"


async def is_allowed(url: str) -> bool:
    """Returns True if robots.txt permits crawling the URL."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url in _CACHE:
        return _CACHE[robots_url]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(robots_url, headers={"User-Agent": _BOT_NAME})
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(resp.text.splitlines())
        allowed = rp.can_fetch(_BOT_NAME, url)
    except Exception:
        allowed = True  # if unreachable, allow (conservative)
    _CACHE[robots_url] = allowed
    return allowed
