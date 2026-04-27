"""PDL (People Data Labs) enrichment node.

Runs after proxycurl_enrich, before validate_email.
Enriches contacts with PDL's professional data: skills, education, seniority.
Skipped silently when PDL_API_KEY is not configured.
Only processes contacts with score > 50 or that have name + company.
"""


from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)

_MIN_SCORE_TO_ENRICH = 50
_MAX_ENRICH_PER_RUN = 20  # PDL credits are expensive


async def pdl_enrich_node(state: XmailState) -> dict:
    from app.config import settings
    from app.scrapers.pdl_client import PDLClient

    if not settings.pdl_api_key:
        logger.info("pdl_skip", reason="no_api_key")
        return {}

    contacts = list(state.get("enriched_contacts", []))
    client = PDLClient(settings.pdl_api_key)
    enriched_count = 0
    budget = _MAX_ENRICH_PER_RUN

    for contact in contacts:
        if budget <= 0:
            break

        score = contact.get("confidence_score", 0)
        has_name_company = contact.get("first_name") and contact.get("company")
        if score < _MIN_SCORE_TO_ENRICH and not has_name_company:
            continue

        try:
            person = None
            email = contact.get("email", "")
            if email:
                person = await client.enrich_by_email(email)

            if not person and has_name_company:
                person = await client.enrich_by_name_company(
                    contact["first_name"],
                    contact.get("last_name", ""),
                    contact["company"],
                )

            if not person:
                continue

            # Merge — don't overwrite existing values
            if person.full_name and not contact.get("name"):
                contact["name"] = person.full_name
            if person.first_name and not contact.get("first_name"):
                contact["first_name"] = person.first_name
            if person.last_name and not contact.get("last_name"):
                contact["last_name"] = person.last_name
            if person.title and not contact.get("title"):
                contact["title"] = person.title
            if person.company and not contact.get("company"):
                contact["company"] = person.company
            if person.linkedin_url and not contact.get("linkedin_url"):
                contact["linkedin_url"] = person.linkedin_url
            if person.country and not contact.get("country"):
                contact["country"] = person.country

            # PDL-specific enrichment data
            contact.setdefault("enrichment_data", {}).update({
                "pdl_industry": person.industry,
                "pdl_seniority": person.seniority,
                "pdl_skills": person.skills,
                "pdl_education": person.education,
                "pdl_likelihood": person.likelihood,
            })

            # Boost confidence for PDL-verified email
            if person.email and person.email.lower() == email.lower() and person.likelihood >= 6:
                contact["confidence_score"] = max(contact.get("confidence_score", 0), 80)

            enriched_count += 1
            budget -= 1

        except Exception as exc:
            logger.warning("pdl_enrich_error", email=contact.get("email"), reason=str(exc))

    logger.info("pdl_enrich_done", enriched=enriched_count, total=len(contacts))
    return {"enriched_contacts": contacts}
