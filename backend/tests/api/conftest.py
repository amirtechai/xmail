"""API-level fixtures — minimal app for tests (no heavy deps needed)."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _build_test_app() -> FastAPI:
    """Minimal FastAPI app with only the routes under test."""
    app = FastAPI(title="Xmail Test")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://test", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    from app.core.exceptions import register_exception_handlers

    register_exception_handlers(app)

    from app.api.routes.auth import router as auth_router
    from app.api.routes.health import router as health_router

    app.include_router(auth_router, prefix="/api")
    app.include_router(health_router, prefix="/api")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict:
        return {"status": "ready"}

    return app


@pytest.fixture(scope="module")
def test_app() -> FastAPI:
    return _build_test_app()


@pytest.fixture
async def async_client(
    mock_session: AsyncMock, test_app: FastAPI
) -> AsyncGenerator[AsyncClient, None]:
    from app.database import get_session

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    test_app.dependency_overrides[get_session] = _override_session
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client
    test_app.dependency_overrides.clear()
