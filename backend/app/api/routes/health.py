"""Detailed health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import CurrentUser, SessionDep
from app.database import get_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/detailed")
async def detailed_health(session: SessionDep, _: CurrentUser) -> dict:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    try:
        redis = await get_redis()
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
