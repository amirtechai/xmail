"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env)
    logger.info("xmail_startup", env=settings.app_env)

    # Warm up bloom filter from DB on startup
    try:
        from sqlalchemy import select

        from app.database import async_session_factory, get_redis
        from app.deduplication.bloom_filter import bf_initialize, bf_warmup
        from app.deduplication.db_checker import load_all_hashes
        from app.deduplication.hasher import hash_email
        from app.models.suppression_list import SuppressionList

        redis = await get_redis()
        await bf_initialize(redis)
        async with async_session_factory() as session:
            discovered = await load_all_hashes(session)
            result = await session.execute(select(SuppressionList.email))
            suppressed = [hash_email(r[0]) for r in result.fetchall()]
        all_hashes = list(set(discovered + suppressed))
        await bf_warmup(redis, all_hashes)
        await redis.close()
        logger.info("bloom_filter_warmed_up", total=len(all_hashes))
    except Exception as exc:
        logger.warning("bloom_filter_warmup_skipped", reason=str(exc))

    yield
    logger.info("xmail_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Xmail API",
        version="1.0.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Security headers (innermost — runs after CORS, on every response)
    from app.core.middleware import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    register_exception_handlers(app)

    # Routers
    from app.api.routes.audience_types import router as audience_types_router
    from app.api.routes.audit_logs import router as audit_logs_router
    from app.api.routes.auth import router as auth_router
    from app.api.routes.bot import router as bot_router
    from app.api.routes.campaigns import router as campaigns_router
    from app.api.routes.contacts import router as contacts_router
    from app.api.routes.health import router as health_router
    from app.api.routes.llm import router as llm_router
    from app.api.routes.reports import router as reports_router
    from app.api.routes.smtp import router as smtp_router
    from app.api.routes.stats import router as stats_router
    from app.api.routes.suppression import router as suppression_router
    from app.api.routes.tracking import router as tracking_router
    from app.api.routes.unsubscribe import router as unsubscribe_router
    from app.api.routes.webhooks import router as webhooks_router

    app.include_router(auth_router, prefix="/api")
    app.include_router(campaigns_router, prefix="/api")
    app.include_router(llm_router, prefix="/api")
    app.include_router(smtp_router, prefix="/api")
    app.include_router(bot_router, prefix="/api")
    app.include_router(audience_types_router, prefix="/api")
    app.include_router(audit_logs_router, prefix="/api")
    app.include_router(suppression_router, prefix="/api")
    app.include_router(contacts_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(stats_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(unsubscribe_router)
    app.include_router(tracking_router)
    app.include_router(webhooks_router, prefix="/api")

    # Prometheus metrics — exposed at /metrics (internal use only, no auth)
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/ready", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict:
        return {"status": "ready"}

    return app


app = create_app()
