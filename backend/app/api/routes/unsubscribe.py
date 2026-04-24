"""Public unsubscribe endpoint — no auth required."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models.suppression_list import SuppressionList, SuppressionReason

router = APIRouter(prefix="/u", tags=["unsubscribe"])


@router.get("/{token}")
async def unsubscribe_page(token: str) -> dict:
    """Returns unsubscribe confirmation page data."""
    return {"token": token, "message": "Click confirm to unsubscribe."}


@router.post("/{token}")
async def confirm_unsubscribe(token: str, session: SessionDep) -> dict:
    """Process unsubscribe request by token (email encoded in token)."""
    # Token = hex-encoded email for simplicity; real impl uses HMAC-signed JWT
    try:
        email = bytes.fromhex(token).decode()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    existing = await session.execute(
        select(SuppressionList).where(SuppressionList.email == email)
    )
    if not existing.scalar_one_or_none():
        suppression = SuppressionList(
            email=email,
            reason=SuppressionReason.UNSUBSCRIBED.value,
        )
        session.add(suppression)
        await session.commit()

    return {"status": "unsubscribed", "email": email}
