"""Bulk email re-verification task using ZeroBounce (or in-house fallback).

Triggered via POST /contacts/verify-bulk.
Processes contacts in batches; updates verified_status, confidence_score, mx_valid.
"""

import asyncio
from datetime import datetime

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.bulk_verify_task.bulk_verify_contacts", bind=True)
def bulk_verify_contacts(self, contact_ids: list[str]) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_run(contact_ids))


async def _run(contact_ids: list[str]) -> dict:
    import uuid

    from sqlalchemy import select

    from app.config import settings
    from app.database import async_session_factory
    from app.models.discovered_contact import DiscoveredContact

    async with async_session_factory() as session:
        result = await session.execute(
            select(DiscoveredContact).where(
                DiscoveredContact.id.in_([uuid.UUID(i) for i in contact_ids])
            )
        )
        contacts = list(result.scalars().all())

    if not contacts:
        return {"verified": 0, "errors": 0}

    emails = [c.email for c in contacts]

    if settings.zerobounce_api_key:
        results = await _verify_zerobounce(emails, settings.zerobounce_api_key)
    else:
        results = await _verify_inhouse(emails)

    result_map = {r["email"]: r for r in results}
    verified = 0
    errors = 0

    async with async_session_factory() as session:
        for contact in contacts:
            r = result_map.get(contact.email)
            if r is None:
                errors += 1
                continue
            contact.verified_status = r["status"]
            contact.confidence_score = r["score"]
            contact.mx_valid = r["mx_valid"]
            contact.is_disposable = r["is_disposable"]
            contact.is_role_based = r["is_role"]
            contact.last_verified_at = datetime.utcnow()
            session.add(contact)
            verified += 1

        await session.commit()

    logger.info("bulk_verify_done", total=len(contacts), verified=verified, errors=errors)
    return {"verified": verified, "errors": errors}


async def _verify_zerobounce(emails: list[str], api_key: str) -> list[dict]:
    from app.email_validator.zerobounce_client import ZeroBounceClient

    client = ZeroBounceClient(api_key)
    zb_results = await client.validate_batch(emails)
    return [
        {
            "email": r.email,
            "status": r.status,
            "score": r.score,
            "mx_valid": r.mx_valid,
            "is_disposable": r.is_disposable,
            "is_role": r.is_role,
        }
        for r in zb_results
    ]


async def _verify_inhouse(emails: list[str]) -> list[dict]:
    import asyncio

    from app.email_validator.validator import validate_email

    semaphore = asyncio.Semaphore(10)

    async def _one(email: str) -> dict:
        async with semaphore:
            try:
                r = await validate_email(email)
                return {
                    "email": email,
                    "status": r.status,
                    "score": r.score,
                    "mx_valid": r.mx_valid,
                    "is_disposable": r.is_disposable,
                    "is_role": r.is_role,
                }
            except Exception:
                return {
                    "email": email,
                    "status": "risky",
                    "score": 30,
                    "mx_valid": False,
                    "is_disposable": False,
                    "is_role": False,
                }

    return list(await asyncio.gather(*[_one(e) for e in emails]))
