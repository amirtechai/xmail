"""Audit log read-only endpoint."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AdminUser, SessionDep
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_type: str
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=AuditLogPage)
async def list_audit_logs(
    session: SessionDep,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = None,
    actor_type: str | None = None,
    resource_type: str | None = None,
) -> AuditLogPage:
    from sqlalchemy import func

    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
    if actor_type:
        q = q.where(AuditLog.actor_type == actor_type)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)

    total_res = await session.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    rows = (
        (await session.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    )
    return AuditLogPage(
        items=[AuditLogOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
