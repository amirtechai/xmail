"""On-demand scraping task — triggered by API or discovery cycle."""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.scraping_task.run_scraping_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_scraping_task(self, campaign_id: str, audience_type: str) -> dict:  # type: ignore[override]
    try:
        return asyncio.get_event_loop().run_until_complete(_scrape(campaign_id, audience_type))
    except Exception as exc:
        logger.error("scraping_task_failed", campaign_id=campaign_id, reason=str(exc))
        raise self.retry(exc=exc) from exc


async def _scrape(campaign_id: str, audience_type: str) -> dict:
    from app.agents.runner import run_discovery
    from app.database import async_session_factory, get_redis

    async with async_session_factory() as session:
        redis = await get_redis()
        try:
            result = await run_discovery(
                campaign_id=campaign_id,
                audience_type=audience_type,
                audience_keywords=[audience_type],
                target_count=100,
                session=session,
                redis_client=redis,
            )
            return {"run_id": str(result.id), "status": result.status}
        finally:
            await redis.close()
