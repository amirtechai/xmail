"""Anti-ban helpers — rate limiting, delays, user-agent rotation."""

import asyncio
import random

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

# Tokens per domain — simple in-memory token bucket
_BUCKETS: dict[str, float] = {}
_RATE = 0.5  # requests per second per domain


def get_random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


async def rate_limit_domain(domain: str) -> None:
    """Non-blocking rate limiter — waits if bucket exhausted."""
    now = asyncio.get_event_loop().time()
    last = _BUCKETS.get(domain, 0.0)
    wait = (1.0 / _RATE) - (now - last)
    if wait > 0:
        await asyncio.sleep(wait + random.uniform(0.1, 0.5))
    _BUCKETS[domain] = asyncio.get_event_loop().time()


async def polite_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))
