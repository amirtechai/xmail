"""MX record check with Redis 24h cache."""

import dns.asyncresolver
import dns.exception

from app.core.logger import get_logger

logger = get_logger(__name__)
_CACHE_TTL = 86400  # 24 hours in seconds


async def has_mx_record(domain: str, redis_client=None) -> bool:  # type: ignore[no-untyped-def]
    cache_key = f"xmail:mx:{domain}"

    if redis_client:
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return cached == b"1"

    try:
        answers = await dns.asyncresolver.resolve(domain, "MX")
        result = len(answers) > 0
    except (dns.exception.DNSException, Exception):
        result = False

    if redis_client:
        await redis_client.setex(cache_key, _CACHE_TTL, b"1" if result else b"0")

    return result
