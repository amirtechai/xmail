"""Periodic discovery cycle task."""

import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.daily_discovery_run.run_discovery_cycle", bind=True)
def run_discovery_cycle(self) -> dict:  # type: ignore[override]
    """Trigger one discovery cycle for all active campaigns."""
    return asyncio.get_event_loop().run_until_complete(_run())


async def _run() -> dict:
    from app.database import async_session_factory
    from app.models.bot_state import BotState, BotStateEnum
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(select(BotState).where(BotState.id == 1))
        state = result.scalar_one_or_none()

        if not state or state.state != BotStateEnum.RUNNING:
            logger.info("discovery_skipped", reason="bot_not_running")
            return {"skipped": True, "reason": "bot_not_running"}

    # Import here to avoid circular imports at module load
    from app.agents.runner import run_discovery

    logger.info("discovery_cycle_started")
    # run_discovery expects a campaign_id and audience_type — here we trigger
    # for all campaigns that are in RUNNING state
    ran = await _dispatch_campaigns()
    logger.info("discovery_cycle_done", campaigns_dispatched=ran)
    return {"campaigns_dispatched": ran}


async def _dispatch_campaigns() -> int:
    from app.database import async_session_factory
    from app.models.campaign import Campaign, CampaignStatus
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(
            select(Campaign).where(Campaign.status == CampaignStatus.RUNNING)
        )
        campaigns = result.scalars().all()

    for campaign in campaigns:
        run_campaign_discovery.delay(str(campaign.id))

    return len(campaigns)


@celery_app.task(name="app.tasks.daily_discovery_run.run_campaign_discovery", bind=True)
def run_campaign_discovery(self, campaign_id: str) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_run_campaign(campaign_id))


async def _run_campaign(campaign_id: str) -> dict:
    from app.agents.runner import run_discovery
    from app.database import async_session_factory, get_redis

    async with async_session_factory() as session:
        redis = await get_redis()
        try:
            result = await run_discovery(
                campaign_id=campaign_id,
                session=session,
                redis=redis,
            )
            return result
        finally:
            await redis.aclose()
