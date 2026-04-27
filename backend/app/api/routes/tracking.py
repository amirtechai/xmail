"""Open tracking pixel and click tracking redirect — no auth required."""

import uuid
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models.sent_email import SentEmail, SentEmailStatus

router = APIRouter(prefix="/t", tags=["tracking"])

# Minimal 1×1 transparent GIF
_PIXEL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00"
    b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)

# Only allow redirects to http/https URLs (no javascript:, data:, etc.)
_ALLOWED_SCHEMES = {"http", "https"}


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


@router.get("/o/{sent_email_id}.gif", include_in_schema=False)
async def track_open(sent_email_id: str, session: SessionDep) -> Response:
    try:
        eid = uuid.UUID(sent_email_id)
    except ValueError:
        return Response(content=_PIXEL_GIF, media_type="image/gif")

    result = await session.execute(select(SentEmail).where(SentEmail.id == eid))
    sent = result.scalar_one_or_none()
    if sent and sent.tracking_pixel_opened_at is None:
        sent.tracking_pixel_opened_at = datetime.utcnow()
        if sent.status not in (SentEmailStatus.CLICKED.value, SentEmailStatus.REPLIED.value):
            sent.status = SentEmailStatus.OPENED.value
        await session.commit()

    return Response(
        content=_PIXEL_GIF,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@router.get("/c/{sent_email_id}", include_in_schema=False)
async def track_click(
    sent_email_id: str,
    session: SessionDep,
    url: str = Query(...),
) -> Response:
    if not _is_safe_url(url):
        return Response(status_code=400, content="Invalid redirect URL")

    try:
        eid = uuid.UUID(sent_email_id)
    except ValueError:
        return RedirectResponse(url=url, status_code=302)

    result = await session.execute(select(SentEmail).where(SentEmail.id == eid))
    sent = result.scalar_one_or_none()
    if sent:
        if sent.clicked_at is None:
            sent.clicked_at = datetime.utcnow()
        sent.status = SentEmailStatus.CLICKED.value
        await session.commit()

    return RedirectResponse(url=url, status_code=302)
