"""Periodic discovery cycle task."""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.daily_discovery_run.run_discovery_cycle", bind=True)
def run_discovery_cycle(self) -> dict:  # type: ignore[override]
    """Trigger one discovery cycle for all active campaigns."""
    return asyncio.get_event_loop().run_until_complete(_run())


async def _run() -> dict:
    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.bot_state import BotState, BotStateEnum

    async with async_session_factory() as session:
        result = await session.execute(select(BotState).where(BotState.id == 1))
        state = result.scalar_one_or_none()

        if not state or state.state not in (BotStateEnum.DISCOVERING, BotStateEnum.SENDING):
            logger.info("discovery_skipped", reason="bot_not_running")
            return {"skipped": True, "reason": "bot_not_running"}

    logger.info("discovery_cycle_started")
    ran = await _dispatch_campaigns()
    logger.info("discovery_cycle_done", campaigns_dispatched=ran)
    return {"campaigns_dispatched": ran}


async def _dispatch_campaigns() -> int:
    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.campaign import Campaign, CampaignStatus

    async with async_session_factory() as session:
        result = await session.execute(
            select(Campaign).where(Campaign.status == CampaignStatus.SEARCHING)
        )
        campaigns = result.scalars().all()

    for campaign in campaigns:
        run_campaign_discovery.delay(str(campaign.id))

    return len(campaigns)


@celery_app.task(name="app.tasks.daily_discovery_run.run_campaign_discovery", bind=True)
def run_campaign_discovery(self, campaign_id: str) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_run_campaign(campaign_id))


async def _run_campaign(campaign_id: str) -> dict:
    import uuid as _uuid

    from sqlalchemy import select

    from app.agents.runner import run_discovery
    from app.database import async_session_factory, get_redis
    from app.models.campaign import Campaign
    from app.models.target_audience_type import TargetAudienceType

    async with async_session_factory() as session:
        redis = await get_redis()
        try:
            result = await session.execute(
                select(Campaign).where(Campaign.id == _uuid.UUID(campaign_id))
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                logger.warning("campaign_not_found", campaign_id=campaign_id)
                return {"error": "campaign_not_found"}

            # Resolve audience labels for the search planner
            audience_keys = campaign.target_audience_type_ids or []
            audience_labels: list[str] = []
            if audience_keys:
                aud_result = await session.execute(
                    select(TargetAudienceType).where(TargetAudienceType.key.in_(audience_keys))
                )
                audience_labels = [a.label_en for a in aud_result.scalars().all()]

            audience_type = audience_labels[0] if audience_labels else (audience_keys[0] if audience_keys else "general")
            run = await run_discovery(
                campaign_id=campaign_id,
                audience_type=audience_type,
                audience_keywords=audience_labels or audience_keys,
                target_count=100,
                session=session,
                redis_client=redis,
            )
            return {"run_id": str(run.id), "status": run.status}
        finally:
            await redis.aclose()
