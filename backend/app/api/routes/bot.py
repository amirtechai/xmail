"""Bot control endpoints — status/pause/stop/run/config + SSE stream."""

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AdminUser, SessionDep
from app.models.agent_run import AgentRun
from app.models.bot_config import BotConfig
from app.models.bot_state import BotState, BotStateEnum

router = APIRouter(prefix="/bot", tags=["bot"])


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _get_or_create_bot_state(session) -> BotState:  # type: ignore[no-untyped-def]
    result = await session.execute(select(BotState).where(BotState.id == 1))
    state = result.scalar_one_or_none()
    if not state:
        state = BotState(id=1)
        session.add(state)
        await session.commit()
        await session.refresh(state)
    return state


async def _get_or_create_bot_config(session) -> BotConfig:  # type: ignore[no-untyped-def]
    result = await session.execute(select(BotConfig).where(BotConfig.id == 1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = BotConfig(id=1)
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)
    return cfg


def _config_to_dict(cfg: BotConfig) -> dict:
    return {
        "enabled_audience_keys": cfg.enabled_audience_keys or [],
        "min_confidence": cfg.min_confidence,
        "target_countries": cfg.target_countries or [],
        "target_languages": cfg.target_languages or [],
        "exclude_domains": cfg.exclude_domains or [],
        "llm_config_id": cfg.llm_config_id,
        "active_hours_start": cfg.active_hours_start,
        "active_hours_end": cfg.active_hours_end,
        "max_emails_per_day": cfg.max_emails_per_day,
        "max_emails_per_hour": cfg.max_emails_per_hour,
        "run_on_weekends": cfg.run_on_weekends,
        "human_in_the_loop": cfg.human_in_the_loop,
        "dry_run": cfg.dry_run,
    }


# ── Schemas ──────────────────────────────────────────────────────────────────


class BotConfigUpdate(BaseModel):
    enabled_audience_keys: list[str] | None = None
    min_confidence: int | None = None
    target_countries: list[str] | None = None
    target_languages: list[str] | None = None
    exclude_domains: list[str] | None = None
    llm_config_id: str | None = None
    active_hours_start: int | None = None
    active_hours_end: int | None = None
    max_emails_per_day: int | None = None
    max_emails_per_hour: int | None = None
    run_on_weekends: bool | None = None
    human_in_the_loop: bool | None = None
    dry_run: bool | None = None


class RunRequest(BaseModel):
    dry_run: bool = False
    run_type: str = "discovery"


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/status")
async def get_status(session: SessionDep, _: AdminUser) -> dict:
    bot = await _get_or_create_bot_state(session)
    return {
        "state": bot.state,
        "is_running": bot.is_running,
        "current_campaign_id": bot.current_campaign_id,
        "daily_email_count": bot.daily_email_count,
        "total_emails_sent": bot.total_emails_sent,
        "last_activity_at": str(bot.last_activity_at) if bot.last_activity_at else None,
        "error_message": bot.error_message,
    }


@router.post("/pause")
async def pause_bot(session: SessionDep, _: AdminUser) -> dict:
    bot = await _get_or_create_bot_state(session)
    if not bot.is_running:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bot is not running")
    bot.state = BotStateEnum.PAUSED.value
    bot.is_running = False
    await session.commit()
    return {"status": "paused"}


@router.post("/stop")
async def stop_bot(session: SessionDep, _: AdminUser) -> dict:
    bot = await _get_or_create_bot_state(session)
    bot.state = BotStateEnum.IDLE.value
    bot.is_running = False
    bot.current_campaign_id = None
    await session.commit()
    return {"status": "stopped"}


@router.post("/run", status_code=202)
async def run_bot(body: RunRequest, session: SessionDep, _: AdminUser) -> dict:
    bot = await _get_or_create_bot_state(session)
    if bot.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bot is already running. Stop it first.",
        )
    cfg = await _get_or_create_bot_config(session)

    if not body.dry_run:
        bot.state = BotStateEnum.DISCOVERING.value
        bot.is_running = True
        await session.commit()

        from app.tasks.daily_discovery_run import run_discovery_cycle

        run_discovery_cycle.delay()

    return {
        "message": "Run started" if not body.dry_run else "Dry run queued",
        "run_type": body.run_type,
        "dry_run": body.dry_run or cfg.dry_run,
        "state": bot.state,
    }


@router.get("/config")
async def get_config(session: SessionDep, _: AdminUser) -> dict:
    cfg = await _get_or_create_bot_config(session)
    return _config_to_dict(cfg)


@router.put("/config")
async def update_config(body: BotConfigUpdate, session: SessionDep, _: AdminUser) -> dict:
    cfg = await _get_or_create_bot_config(session)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cfg, field, value)
    await session.commit()
    await session.refresh(cfg)
    return _config_to_dict(cfg)


@router.get("/runs")
async def list_runs(session: SessionDep, _: AdminUser) -> list:
    result = await session.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(50))
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "run_type": r.run_type,
            "status": r.status,
            "started_at": str(r.started_at),
            "finished_at": str(r.finished_at) if r.finished_at else None,
            "contacts_found": r.contacts_discovered,
            "error_message": r.error_message,
        }
        for r in runs
    ]


@router.get("/stream")
async def event_stream(session: SessionDep, _: AdminUser) -> StreamingResponse:
    """SSE — real-time bot state, 1 tick/sec, max 120 ticks."""

    async def generator() -> AsyncGenerator[str, None]:
        for _ in range(120):
            bot = await _get_or_create_bot_state(session)
            data = json.dumps(
                {
                    "state": bot.state,
                    "is_running": bot.is_running,
                    "daily_email_count": bot.daily_email_count,
                }
            )
            yield f"data: {data}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
