"""Hunter.io lookup node — enriches pipeline with domain-search results.

Runs after infer_email_pattern, before score_contact.
Skipped silently when HUNTER_API_KEY is not configured.
"""

from urllib.parse import urlparse

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)

_MAX_DOMAINS = 5      # API quota guard per pipeline run
_MAX_PER_DOMAIN = 100  # Hunter hard max per domain-search call


def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    if "://" not in url:
        url = f"https://{url}"
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _confidence_to_status(confidence: int) -> str:
    if confidence >= 90:
        return "valid"
    if confidence >= 70:
        return "catch_all"
    return "risky"


async def hunter_lookup_node(state: XmailState) -> dict:
    from app.config import settings
    from app.scrapers.hunter_client import HunterClient

    if not settings.hunter_api_key:
        logger.info("hunter_skip", reason="no_api_key")
        return {}

    contacts = state.get("deduplicated_contacts", [])
    existing_emails = {c["email"].lower() for c in contacts}

    # Collect unique domains from contact websites and email addresses
    domains: list[str] = []
    seen: set[str] = set()
    for c in contacts:
        for source in (c.get("website") or "", c.get("email") or ""):
            domain = (
                _extract_domain(source)
                if "." in source
                else (source.split("@")[1].lower() if "@" in source else None)
            )
            if domain and domain not in seen:
                domains.append(domain)
                seen.add(domain)

    if not domains:
        return {}

    client = HunterClient(settings.hunter_api_key)
    new_contacts: list[dict] = []

    for domain in domains[:_MAX_DOMAINS]:
        try:
            results = await client.domain_search(domain, limit=_MAX_PER_DOMAIN)
            for h in results:
                if h.email.lower() in existing_emails:
                    continue
                name_parts = [h.first_name or "", h.last_name or ""]
                new_contacts.append({
                    "email": h.email.lower(),
                    "name": " ".join(p for p in name_parts if p) or None,
                    "first_name": h.first_name,
                    "last_name": h.last_name,
                    "title": h.position,
                    "company": domain,
                    "website": f"https://{domain}",
                    "linkedin_url": h.linkedin_url,
                    "verified_status": _confidence_to_status(h.confidence),
                    "confidence_score": h.confidence,
                    "source": "hunter",
                })
                existing_emails.add(h.email.lower())
        except Exception as exc:
            logger.warning("hunter_domain_error", domain=domain, reason=str(exc))

    if new_contacts:
        logger.info("hunter_found", count=len(new_contacts), domains=len(domains[:_MAX_DOMAINS]))
        return {"deduplicated_contacts": contacts + new_contacts}

    return {}
