"""Agent runner — entry point for launching and resuming discovery runs."""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_graph
from app.agents.state import XmailState
from app.core.logger import get_logger
from app.llm.router import build_provider
from app.models.agent_run import AgentRun, RunStatus, RunType

logger = get_logger(__name__)


async def run_discovery(
    campaign_id: str,
    audience_type: str,
    audience_keywords: list[str],
    target_count: int,
    llm_config,
    session: AsyncSession,
    redis_client,
) -> AgentRun:
    run = AgentRun(
        id=uuid.uuid4(),
        run_type=RunType.DISCOVERY.value,
        status=RunStatus.RUNNING.value,
        campaign_id=uuid.UUID(campaign_id),
        langgraph_thread_id=str(uuid.uuid4()),
    )
    session.add(run)
    await session.commit()

    initial_state: XmailState = {
        "campaign_id": campaign_id,
        "audience_type": audience_type,
        "audience_keywords": audience_keywords,
        "target_count": target_count,
        "search_queries": [],
        "raw_urls": [],
        "crawled_pages": [],
        "extracted_emails": [],
        "enriched_contacts": [],
        "validated_contacts": [],
        "deduplicated_contacts": [],
        "persisted_count": 0,
        "error": None,
        "retry_count": 0,
        "max_retries": 2,
        "messages": [],
    }

    try:
        llm_provider = build_provider(llm_config)
        compiled = build_graph(llm_provider, session, redis_client)
        config = {"configurable": {"thread_id": run.langgraph_thread_id}}
        final_state = await compiled.ainvoke(initial_state, config=config)
        run.status = RunStatus.COMPLETED.value
        run.contacts_discovered = final_state.get("persisted_count", 0)
    except Exception as exc:
        logger.error("agent_run_failed", run_id=str(run.id), error=str(exc))
        run.status = RunStatus.FAILED.value
        run.error_message = str(exc)[:500]
    finally:
        run.finished_at = datetime.utcnow()
        await session.commit()

    return run
