"""Apollo.io lookup node — finance-targeted people search.

Runs after dedupe, before infer_email_pattern.
Skipped silently when APOLLO_API_KEY is not configured.
Adds verified finance professionals to deduplicated_contacts.
"""

import logging

from app.agents.state import XmailState

logger = logging.getLogger(__name__)

_MAX_PAGES = 3
_PER_PAGE = 25


def _email_status_to_verified(status: str) -> str:
    mapping = {
        "verified": "valid",
        "likely to engage": "catch_all",
        "guessed": "risky",
        "unavailable": "unknown",
        "bounced": "invalid",
    }
    return mapping.get(status.lower(), "unknown")


async def apollo_lookup_node(state: XmailState) -> dict:
    from app.config import settings
    from app.scrapers.apollo_client import ApolloClient

    if not settings.apollo_api_key:
        logger.info("apollo_skip", reason="no_api_key")
        return {}

    contacts = list(state.get("deduplicated_contacts", []))
    existing_emails = {c["email"].lower() for c in contacts}
    keywords = state.get("audience_keywords") or []

    client = ApolloClient(settings.apollo_api_key)
    new_contacts: list[dict] = []

    for page in range(1, _MAX_PAGES + 1):
        try:
            people = await client.finance_people_search(keywords=keywords or None, page=page, per_page=_PER_PAGE)
        except Exception as exc:
            logger.warning("apollo_search_error", page=page, error=str(exc))
            break

        if not people:
            break

        for person in people:
            if person.email in existing_emails:
                continue
            name_parts = [person.first_name or "", person.last_name or ""]
            new_contacts.append({
                "email": person.email,
                "name": " ".join(p for p in name_parts if p) or None,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "title": person.title,
                "company": person.company,
                "website": f"https://{person.company_domain}" if person.company_domain else None,
                "linkedin_url": person.linkedin_url,
                "city": person.city,
                "country": person.country,
                "verified_status": _email_status_to_verified(person.email_status),
                "confidence_score": 85 if person.email_status == "verified" else 60,
                "seniority": person.seniority,
                "departments": person.departments,
                "source": "apollo",
            })
            existing_emails.add(person.email)

        # Stop early if we already found enough
        target = state.get("target_count", 100)
        if len(contacts) + len(new_contacts) >= target:
            break

    if new_contacts:
        logger.info("apollo_found", count=len(new_contacts))
        return {"deduplicated_contacts": contacts + new_contacts}

    return {}
