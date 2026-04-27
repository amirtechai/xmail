"""Proxycurl enrich node — augments contacts that have a linkedin_url."""

from app.agents.state import XmailState
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


async def proxycurl_enrich_node(state: XmailState) -> dict:
    if not settings.proxycurl_api_key:
        return {}

    from app.scrapers.proxycurl_client import extract_fields, fetch_linkedin_profile

    contacts = list(state.get("enriched_contacts", []))
    enriched_count = 0

    for contact in contacts:
        linkedin_url = contact.get("linkedin_url")
        if not linkedin_url:
            continue

        try:
            profile = await fetch_linkedin_profile(linkedin_url, settings.proxycurl_api_key)
            if not profile:
                continue

            fields = extract_fields(profile)
            for key, value in fields.items():
                if value and not contact.get(key):
                    contact[key] = value

            contact["proxycurl_raw"] = profile
            enriched_count += 1
        except Exception as exc:
            logger.warning("proxycurl_enrich_failed", linkedin_url=linkedin_url, reason=str(exc))

    logger.info("proxycurl_enrich_done", enriched=enriched_count, total=len(contacts))
    return {"enriched_contacts": contacts}
