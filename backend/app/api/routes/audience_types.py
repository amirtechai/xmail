"""Audience types listing — grouped by category."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.models.discovered_contact import DiscoveredContact
from app.models.target_audience_type import TargetAudienceType

router = APIRouter(prefix="/audience-types", tags=["audience-types"])


@router.get("/")
async def list_audience_types(session: SessionDep, _: CurrentUser) -> dict:
    # All types
    rows = (
        await session.execute(
            select(TargetAudienceType).order_by(
                TargetAudienceType.category, TargetAudienceType.label_en
            )
        )
    ).scalars().all()

    # Contact counts per audience key
    count_rows = (
        await session.execute(
            select(
                DiscoveredContact.audience_type_key.label("key"),
                func.count().label("cnt"),
            ).group_by(DiscoveredContact.audience_type_key)
        )
    ).all()
    counts = {r.key: r.cnt for r in count_rows}

    # Group by category
    grouped: dict[str, list[dict]] = {}
    for t in rows:
        cat = t.category
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "key": t.key,
            "label_en": t.label_en,
            "label_tr": t.label_tr,
            "description": t.description,
            "icon_name": t.icon_name,
            "is_enabled_default": t.is_enabled_default,
            "contact_count": counts.get(t.key, 0),
        })

    return {
        "categories": [
            {"name": cat, "types": types}
            for cat, types in grouped.items()
        ],
        "total": len(rows),
    }


class AudienceTypeToggle(BaseModel):
    is_enabled_default: bool


@router.patch("/{key}")
async def toggle_audience_type(
    key: str,
    body: AudienceTypeToggle,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    result = await session.execute(
        select(TargetAudienceType).where(TargetAudienceType.key == key)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience type not found")
    t.is_enabled_default = body.is_enabled_default
    await session.commit()
    return {"key": t.key, "is_enabled_default": t.is_enabled_default}
