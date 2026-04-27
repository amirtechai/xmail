"""Domain bulk targeting — Hunter domain_search for known finance firm domains.

Celery beat task: runs daily, generates verified finance contacts from known firm domains.
"""

import asyncio
import hashlib
import logging
import uuid

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Known finance firm domains — authoritative list, extend as needed
FINANCE_DOMAINS = [
    "gs.com",
    "jpmchase.com",
    "morganstanley.com",
    "blackrock.com",
    "vanguard.com",
    "fidelity.com",
    "citadel.com",
    "bridgewater.com",
    "renaissancetech.com",
    "deshaw.com",
    "twosigma.com",
    "kkr.com",
    "blackstone.com",
    "carlyle.com",
    "apolloglobal.com",
    "bain.com",
    "tpg.com",
    "warburg.com",
    "sequoiacap.com",
    "a16z.com",
    "berkshirehathaway.com",
    "pimco.com",
    "invesco.com",
    "schroders.com",
    "aberdeen.com",
    "wellington.com",
    "troweprice.com",
    "franklintempleton.com",
    "alliancebernstein.com",
]

_MAX_DOMAINS_PER_RUN = 10
_HUNTER_LIMIT = 100


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


@celery_app.task(name="app.tasks.domain_bulk_targeting.celery_domain_bulk_targeting", bind=True)
def celery_domain_bulk_targeting(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_run())


async def _run() -> dict:
    from app.database import async_session_factory

    async with async_session_factory() as session:
        return await run_domain_bulk_targeting(session)


async def run_domain_bulk_targeting(session) -> dict:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from app.config import settings
    from app.models.discovered_contact import DiscoveredContact
    from app.scrapers.hunter_client import HunterClient

    if not settings.hunter_api_key:
        logger.info("domain_bulk_skip", reason="no_hunter_api_key")
        return {"skipped": True}

    client = HunterClient(settings.hunter_api_key)
    new_count = 0
    errors = 0

    for domain in FINANCE_DOMAINS[:_MAX_DOMAINS_PER_RUN]:
        try:
            results = await client.domain_search(domain, limit=_HUNTER_LIMIT)
            for h in results:
                if not h.email:
                    continue

                email = h.email.lower().strip()
                eh = _email_hash(email)

                exists = await session.execute(
                    select(DiscoveredContact).where(DiscoveredContact.email_hash == eh)
                )
                if exists.scalar_one_or_none():
                    continue

                name_parts = [h.first_name or "", h.last_name or ""]
                full_name = " ".join(p for p in name_parts if p) or None
                verified = (
                    "valid" if h.confidence >= 90
                    else "catch_all" if h.confidence >= 70
                    else "risky"
                )
                contact = DiscoveredContact(
                    id=uuid.uuid4(),
                    email=email,
                    email_hash=eh,
                    full_name=full_name,
                    first_name=h.first_name,
                    last_name=h.last_name,
                    title=h.position,
                    company=domain,
                    website=f"https://{domain}",
                    linkedin_url=h.linkedin_url,
                    verified_status=verified,
                    confidence_score=h.confidence,
                    source_type="hunter_bulk",
                    audience_type_key="finance",
                    enrichment_data={"industry": "finance", "source_domain": domain},
                )
                session.add(contact)
                new_count += 1

            await session.commit()
            logger.info("domain_bulk_domain_done", domain=domain, found=len(results))

        except Exception as exc:
            await session.rollback()
            logger.warning("domain_bulk_domain_error", domain=domain, error=str(exc))
            errors += 1

    logger.info("domain_bulk_complete", new_contacts=new_count, errors=errors)
    return {
        "new_contacts": new_count,
        "errors": errors,
        "domains_processed": min(len(FINANCE_DOMAINS), _MAX_DOMAINS_PER_RUN),
    }
