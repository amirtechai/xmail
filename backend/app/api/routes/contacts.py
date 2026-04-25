"""Discovered contacts endpoints — list, sort, filter, export, bulk delete, update, import."""

import csv
import hashlib
import io
import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser, get_session
from app.models.discovered_contact import DiscoveredContact
from app.schemas.contact import BulkDeleteRequest, ContactUpdate, ImportResult, VerifyBulkRequest

router = APIRouter(prefix="/contacts", tags=["contacts"])

_SORT_COLUMNS: dict[str, object] = {
    "email": DiscoveredContact.email,
    "full_name": DiscoveredContact.full_name,
    "company": DiscoveredContact.company,
    "title": DiscoveredContact.title,
    "confidence_score": DiscoveredContact.confidence_score,
    "verified_status": DiscoveredContact.verified_status,
    "discovered_at": DiscoveredContact.discovered_at,
    "audience_type_key": DiscoveredContact.audience_type_key,
    "country": DiscoveredContact.country,
}


_MAX_IMPORT_ROWS = 5_000

_COLUMN_ALIASES: dict[str, str] = {
    "name": "full_name",
    "title": "job_title",
    "job title": "job_title",
    "full name": "full_name",
    "first name": "first_name",
    "last name": "last_name",
    "linkedin": "linkedin_url",
    "twitter": "twitter_handle",
    "audience": "audience_type",
    "audience type": "audience_type",
}


def _normalise_header(h: str) -> str:
    clean = h.strip().lower().replace("-", "_").replace(" ", "_")
    return _COLUMN_ALIASES.get(h.strip().lower(), clean)


def _parse_csv(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []
    headers = [_normalise_header(f) for f in reader.fieldnames]
    rows = []
    for raw in reader:
        rows.append({headers[i]: (v or "").strip() for i, v in enumerate(raw.values())})
    return rows


def _parse_xlsx(content: bytes) -> list[dict[str, str]]:
    import openpyxl  # lazy import — only used for XLSX uploads

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return []
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not all_rows:
        return []
    headers = [_normalise_header(str(h)) if h is not None else "" for h in all_rows[0]]
    result = []
    for row in all_rows[1:]:
        d = {headers[i]: str(v).strip() if v is not None else "" for i, v in enumerate(row) if i < len(headers)}
        result.append(d)
    return result


def _serialize(c: DiscoveredContact) -> dict:
    return {
        "id": str(c.id),
        "email": c.email,
        "full_name": c.full_name,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "job_title": c.title,
        "company": c.company,
        "website": c.website,
        "linkedin_url": c.linkedin_url,
        "twitter_handle": c.twitter_handle,
        "source_url": c.source_url,
        "source_type": c.source_type,
        "audience_type": c.audience_type_key,
        "country": c.country,
        "language": c.language,
        "confidence_score": c.confidence_score,
        "relevance_score": c.relevance_score,
        "verified_status": c.verified_status if isinstance(c.verified_status, str) else (c.verified_status.value if c.verified_status else None),
        "mx_valid": c.mx_valid,
        "smtp_valid": c.smtp_valid,
        "is_disposable": c.is_disposable,
        "is_role_based": c.is_role_based,
        "created_at": c.discovered_at.isoformat(),
    }


@router.get("/")
async def list_contacts(
    _: CurrentUser,
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = None,
    audience_type: str | None = None,
    verified_status: str | None = None,
    country: str | None = None,
    language: str | None = None,
    min_confidence: int | None = Query(None, ge=0, le=100),
    max_confidence: int | None = Query(None, ge=0, le=100),
    sort_by: str = Query("discovered_at", pattern=r"^[a-z_]+$"),
    sort_dir: str = Query("desc", pattern=r"^(asc|desc)$"),
) -> dict:
    q = select(DiscoveredContact)

    if search:
        q = q.where(
            or_(
                DiscoveredContact.email.ilike(f"%{search}%"),
                DiscoveredContact.company.ilike(f"%{search}%"),
                DiscoveredContact.full_name.ilike(f"%{search}%"),
            )
        )
    if audience_type:
        q = q.where(DiscoveredContact.audience_type_key == audience_type)
    if verified_status:
        q = q.where(DiscoveredContact.verified_status == verified_status)
    if country:
        q = q.where(DiscoveredContact.country == country.upper())
    if language:
        q = q.where(DiscoveredContact.language == language.lower())
    if min_confidence is not None:
        q = q.where(DiscoveredContact.confidence_score >= min_confidence)
    if max_confidence is not None:
        q = q.where(DiscoveredContact.confidence_score <= max_confidence)

    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()

    col = _SORT_COLUMNS.get(sort_by, DiscoveredContact.discovered_at)
    order = desc(col).nulls_last() if sort_dir == "desc" else asc(col).nulls_last()
    q = q.order_by(order).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()

    return {"items": [_serialize(c) for c in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/export")
async def export_contacts(
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
    fmt: str = Query("csv", pattern=r"^(csv|json)$"),
    audience_type: str | None = None,
    verified_status: str | None = None,
    min_confidence: int | None = Query(None, ge=0, le=100),
) -> Response:
    q = select(DiscoveredContact)
    if audience_type:
        q = q.where(DiscoveredContact.audience_type_key == audience_type)
    if verified_status:
        q = q.where(DiscoveredContact.verified_status == verified_status)
    if min_confidence is not None:
        q = q.where(DiscoveredContact.confidence_score >= min_confidence)
    q = q.order_by(DiscoveredContact.discovered_at.desc())

    rows = (await session.execute(q)).scalars().all()
    data = [_serialize(c) for c in rows]

    if fmt == "json":
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=contacts.json"},
        )

    buf = io.StringIO()
    if data:
        writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)

    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts.csv"},
    )


@router.patch("/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(DiscoveredContact).where(DiscoveredContact.id == contact_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    patch = body.model_dump(exclude_none=True)
    field_map = {"job_title": "title", "audience_type_key": "audience_type_key"}
    for field, value in patch.items():
        setattr(c, field_map.get(field, field), value)

    await session.commit()
    await session.refresh(c)
    return _serialize(c)


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_contacts(
    body: BulkDeleteRequest,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not body.ids:
        return {"deleted": 0}

    uuids = []
    for raw in body.ids:
        try:
            uuids.append(uuid.UUID(raw))
        except ValueError:
            pass

    if not uuids:
        return {"deleted": 0}

    result = await session.execute(
        select(DiscoveredContact).where(DiscoveredContact.id.in_(uuids))
    )
    contacts = result.scalars().all()
    for c in contacts:
        await session.delete(c)
    await session.commit()
    return {"deleted": len(contacts)}


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_200_OK)
async def import_contacts(
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
    file: UploadFile = File(...),
    audience_type: str = Query("imported", pattern=r"^[a-z0-9_\-]{1,100}$"),
) -> ImportResult:
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .csv and .xlsx files are supported")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB guard
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10 MB limit")

    rows = _parse_xlsx(content) if filename.lower().endswith(".xlsx") else _parse_csv(content)

    if not rows:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is empty or has no parseable rows")
    if len(rows) > _MAX_IMPORT_ROWS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File exceeds {_MAX_IMPORT_ROWS} row limit")

    # Collect all candidate emails for a single bulk existence check
    candidate_emails: list[str] = []
    for row in rows:
        e = row.get("email", "").strip().lower()
        if e:
            candidate_emails.append(e)

    existing: set[str] = set(
        (await session.execute(
            select(DiscoveredContact.email).where(DiscoveredContact.email.in_(candidate_emails))
        )).scalars().all()
    )

    imported = 0
    skipped = 0
    errors: list[dict] = []

    for idx, row in enumerate(rows):
        row_num = idx + 2  # 1-indexed + header
        email = row.get("email", "").strip().lower()

        if not email:
            errors.append({"row": row_num, "email": "", "error": "Missing email"})
            continue

        at = email.count("@")
        domain_part = email.split("@")[-1] if at == 1 else ""
        if at != 1 or "." not in domain_part or len(email) > 254:
            errors.append({"row": row_num, "email": email, "error": "Invalid email format"})
            continue

        if email in existing:
            skipped += 1
            continue

        email_hash = hashlib.sha256(email.encode()).hexdigest()
        raw_country = (row.get("country") or "").strip().upper()
        raw_lang = (row.get("language") or "").strip().lower()

        contact = DiscoveredContact(
            email=email,
            email_hash=email_hash,
            full_name=row.get("full_name") or None,
            first_name=row.get("first_name") or None,
            last_name=row.get("last_name") or None,
            title=row.get("job_title") or None,
            company=row.get("company") or None,
            website=row.get("website") or None,
            linkedin_url=row.get("linkedin_url") or None,
            twitter_handle=row.get("twitter_handle") or None,
            country=raw_country[:2] if raw_country else None,
            language=raw_lang[:10] if raw_lang else None,
            source_url=f"import://{filename}",
            source_type="import",
            audience_type_key=row.get("audience_type") or audience_type,
            verified_status="unverified",
            confidence_score=50,
        )
        session.add(contact)
        existing.add(email)
        imported += 1

        if imported % 200 == 0:
            await session.flush()

    await session.commit()
    return ImportResult(imported=imported, skipped=skipped, errors=[{"row": e["row"], "email": e["email"], "error": e["error"]} for e in errors[:50]])


@router.post("/{contact_id}/enrich-linkedin")
async def enrich_linkedin(
    contact_id: uuid.UUID,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Enrich a single contact with LinkedIn data via Proxycurl."""
    from app.config import settings

    if not settings.proxycurl_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PROXYCURL_API_KEY is not configured.",
        )

    contact = (await session.execute(
        select(DiscoveredContact).where(DiscoveredContact.id == contact_id)
    )).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    if not contact.linkedin_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Contact has no LinkedIn URL to enrich.",
        )

    from app.scrapers.proxycurl_client import extract_fields, fetch_linkedin_profile

    try:
        profile = await fetch_linkedin_profile(contact.linkedin_url, settings.proxycurl_api_key)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LinkedIn profile not found via Proxycurl.",
        )

    fields = extract_fields(profile)
    for key, value in fields.items():
        if value and not getattr(contact, key, None):
            setattr(contact, key, value)

    meta = contact.enrichment_data or {}
    meta["proxycurl"] = {k: profile.get(k) for k in ("headline", "summary", "city", "experiences")}
    contact.enrichment_data = meta

    await session.commit()
    await session.refresh(contact)

    return {
        "id": str(contact.id),
        "email": contact.email,
        "full_name": contact.full_name,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "title": contact.title,
        "company": contact.company,
        "country": contact.country,
        "twitter_handle": contact.twitter_handle,
        "linkedin_url": contact.linkedin_url,
        "enriched": True,
    }


@router.post("/verify-bulk", status_code=status.HTTP_202_ACCEPTED)
async def verify_bulk(
    body: VerifyBulkRequest,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if body.ids is not None:
        contact_ids = [str(i) for i in body.ids]
    else:
        # Queue all currently unverified contacts (up to 5000 at a time)
        rows = (await session.execute(
            select(DiscoveredContact.id)
            .where(DiscoveredContact.verified_status == "unverified")
            .limit(5000)
        )).scalars().all()
        contact_ids = [str(r) for r in rows]

    if not contact_ids:
        return {"queued": 0, "task_id": None}

    from app.tasks.bulk_verify_task import bulk_verify_contacts

    task = bulk_verify_contacts.delay(contact_ids)
    return {"queued": len(contact_ids), "task_id": task.id}
