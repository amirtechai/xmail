"""Redis-backed bloom filter for fast email deduplication.

Capacity: 10M items, false-positive rate: 0.001 (0.1%).
Uses Redis BF (RedisBloom) commands via redis-py.
"""

from collections.abc import Sequence

from redis.asyncio import Redis

from app.core.logger import get_logger

logger = get_logger(__name__)

BF_KEY = "xmail:dedup:bloom"
BF_CAPACITY = 10_000_000
BF_ERROR_RATE = 0.001


async def bf_initialize(redis: Redis) -> None:
    """Create bloom filter if it doesn't exist."""
    try:
        await redis.execute_command("BF.RESERVE", BF_KEY, BF_ERROR_RATE, BF_CAPACITY, "NONSCALING")
        logger.info("bloom_filter_created", key=BF_KEY, capacity=BF_CAPACITY)
    except Exception as exc:
        # BF.RESERVE raises if key already exists — that's fine
        if "already exists" not in str(exc).lower():
            logger.warning("bloom_filter_reserve_error", reason=str(exc))


async def bf_add(redis: Redis, email_hash: str) -> bool:
    """Add hash to bloom filter. Returns True if newly inserted."""
    result = await redis.execute_command("BF.ADD", BF_KEY, email_hash)
    return bool(result)


async def bf_exists(redis: Redis, email_hash: str) -> bool:
    """Check if hash may exist in bloom filter. False = definitely not seen."""
    result = await redis.execute_command("BF.EXISTS", BF_KEY, email_hash)
    return bool(result)


async def bf_add_batch(redis: Redis, hashes: Sequence[str]) -> list[bool]:
    """Add multiple hashes at once. Returns list of insertion results."""
    if not hashes:
        return []
    results = await redis.execute_command("BF.MADD", BF_KEY, *hashes)
    return [bool(r) for r in results]


async def bf_exists_batch(redis: Redis, hashes: Sequence[str]) -> list[bool]:
    """Check multiple hashes at once."""
    if not hashes:
        return []
    results = await redis.execute_command("BF.MEXISTS", BF_KEY, *hashes)
    return [bool(r) for r in results]


async def bf_warmup(redis: Redis, hashes: list[str]) -> int:
    """Load existing hashes into bloom filter on startup. Returns count loaded."""
    if not hashes:
        return 0

    # Process in batches of 1000 to avoid huge commands
    batch_size = 1000
    loaded = 0
    for i in range(0, len(hashes), batch_size):
        batch = hashes[i : i + batch_size]
        await redis.execute_command("BF.MADD", BF_KEY, *batch)
        loaded += len(batch)

    logger.info("bloom_filter_warmed_up", hashes_loaded=loaded)
    return loaded
