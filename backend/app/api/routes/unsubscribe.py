"""Public unsubscribe endpoint — no auth required."""

import uuid

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models.sent_email import SentEmail, SentEmailStatus
from app.models.suppression_list import SuppressionList, SuppressionReason

router = APIRouter(prefix="/u", tags=["unsubscribe"])

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #0f0f0f; color: #d4d4d4; display: flex;
           align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
    .card {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
             padding: 2rem; max-width: 420px; width: 100%; text-align: center; }}
    h1 {{ font-size: 1.1rem; color: #e5e5e5; margin-bottom: 0.5rem; }}
    p {{ font-size: 0.875rem; color: #888; margin-bottom: 1.5rem; }}
    form {{ margin: 0; }}
    button {{ background: #ef4444; color: #fff; border: none; border-radius: 6px;
              padding: 0.625rem 1.5rem; font-size: 0.875rem; cursor: pointer;
              transition: background 0.15s; }}
    button:hover {{ background: #dc2626; }}
    .done {{ color: #4ade80; font-size: 0.875rem; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{heading}</h1>
    <p>{body}</p>
    {action}
  </div>
</body>
</html>"""


@router.get("/{token}", response_class=HTMLResponse)
async def unsubscribe_page(token: str) -> HTMLResponse:
    try:
        uuid.UUID(token)
        valid = True
    except ValueError:
        valid = False

    if not valid:
        return HTMLResponse(
            _PAGE_TEMPLATE.format(
                title="Invalid Link",
                heading="Invalid unsubscribe link",
                body="This link is not valid. Please contact support if you believe this is an error.",
                action="",
            ),
            status_code=400,
        )

    return HTMLResponse(
        _PAGE_TEMPLATE.format(
            title="Unsubscribe",
            heading="Unsubscribe from this mailing list",
            body="Click the button below to confirm. You will no longer receive emails from us.",
            action=f"""<form method="POST" action="/u/{token}">
              <button type="submit">Confirm Unsubscribe</button>
            </form>""",
        )
    )


@router.post("/{token}", response_class=HTMLResponse)
async def confirm_unsubscribe(token: str, session: SessionDep) -> HTMLResponse:
    try:
        eid = uuid.UUID(token)
    except ValueError:
        return HTMLResponse(
            _PAGE_TEMPLATE.format(
                title="Invalid Link",
                heading="Invalid unsubscribe link",
                body="This link is not valid.",
                action="",
            ),
            status_code=400,
        )

    result = await session.execute(select(SentEmail).where(SentEmail.id == eid))
    sent = result.scalar_one_or_none()

    email: str | None = None
    if sent:
        email = sent.recipient_email
        if sent.status not in (SentEmailStatus.BOUNCED.value,):
            sent.status = SentEmailStatus.UNSUBSCRIBED.value

    if not email:
        return HTMLResponse(
            _PAGE_TEMPLATE.format(
                title="Already Processed",
                heading="Already unsubscribed",
                body="This request has already been processed or the link has expired.",
                action="",
            )
        )

    existing = await session.execute(
        select(SuppressionList).where(SuppressionList.email == email)
    )
    if not existing.scalar_one_or_none():
        session.add(SuppressionList(
            email=email,
            reason=SuppressionReason.UNSUBSCRIBED.value,
        ))
    await session.commit()

    return HTMLResponse(
        _PAGE_TEMPLATE.format(
            title="Unsubscribed",
            heading="You have been unsubscribed",
            body=f"<strong>{email}</strong> has been removed from our mailing list.",
            action='<p class="done">✓ Done</p>',
        )
    )
