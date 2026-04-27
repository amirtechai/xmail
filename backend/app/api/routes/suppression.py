"""Suppression list management endpoints."""

import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser, get_session
from app.core.exceptions import NotFoundError
from app.models.suppression_list import SuppressionList, SuppressionReason
from app.schemas.suppression import (
    SuppressionAddRequest,
    SuppressionListResponse,
    SuppressionOut,
)

router = APIRouter(prefix="/suppression", tags=["suppression"])


@router.get("/", response_model=SuppressionListResponse)
async def list_suppressed(
    _: CurrentUser,
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    reason: SuppressionReason | None = None,
    search: str | None = None,
) -> SuppressionListResponse:
    offset = (page - 1) * page_size
    q = select(SuppressionList).order_by(SuppressionList.added_at.desc())
    if reason:
        q = q.where(SuppressionList.reason == reason)
    if search:
        q = q.where(SuppressionList.email.ilike(f"%{search}%"))

    total_result = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()

    rows_result = await session.execute(q.offset(offset).limit(page_size))
    items = [SuppressionOut.model_validate(r) for r in rows_result.scalars()]

    return SuppressionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/export")
async def export_suppression(
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
    reason: SuppressionReason | None = None,
) -> StreamingResponse:
    q = select(SuppressionList).order_by(SuppressionList.added_at.desc())
    if reason:
        q = q.where(SuppressionList.reason == reason)
    rows = (await session.execute(q)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["email", "reason", "notes", "added_at"])
    for r in rows:
        writer.writerow([r.email, r.reason, r.notes or "", str(r.added_at)])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=suppression_list.csv"},
    )


class BulkImportRequest(BaseModel):
    emails: list[str]
    reason: str = "manual"
    notes: str | None = None


class BulkImportResponse(BaseModel):
    added: int
    skipped: int


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import(
    body: BulkImportRequest,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> BulkImportResponse:
    from app.deduplication.hasher import hash_email, normalize_email

    added = 0
    skipped = 0
    for raw_email in body.emails:
        email = normalize_email(raw_email.strip())
        if not email:
            skipped += 1
            continue
        h = hash_email(email)
        existing = (await session.execute(
            select(SuppressionList).where(SuppressionList.email_hash == h)
        )).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        session.add(SuppressionList(email=email, email_hash=h, reason=body.reason, notes=body.notes))
        added += 1

    await session.commit()
    return BulkImportResponse(added=added, skipped=skipped)


@router.post("/", response_model=SuppressionOut, status_code=201)
async def add_suppression(
    body: SuppressionAddRequest,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> SuppressionOut:
    from app.deduplication.hasher import hash_email, normalize_email

    email_normalized = normalize_email(body.email)
    entry = SuppressionList(
        email=email_normalized,
        email_hash=hash_email(email_normalized),
        reason=body.reason.value if hasattr(body.reason, "value") else body.reason,
        notes=body.notes,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return SuppressionOut.model_validate(entry)


@router.delete("/{suppression_id}", status_code=204)
async def remove_suppression(
    suppression_id: uuid.UUID,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(SuppressionList).where(SuppressionList.id == suppression_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("Suppression entry not found")
    await session.delete(entry)
    await session.commit()


@router.delete("/email/{email}", status_code=204)
async def remove_suppression_by_email(
    email: str,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    await session.execute(
        delete(SuppressionList).where(SuppressionList.email == email.lower().strip())
    )
    await session.commit()
