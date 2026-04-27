"""Score contact node — 0–100 confidence score based on available signals."""

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)


def _compute_score(contact: dict) -> int:
    score = 0

    # Validation quality (max 40)
    status = contact.get("verified_status", "unverified")
    score += {"valid": 40, "catch_all": 20, "risky": 10, "unverified": 5}.get(status, 0)

    # Enrichment completeness (max 30)
    if contact.get("name"):
        score += 10
    if contact.get("company"):
        score += 10
    if contact.get("title"):
        score += 10

    # Professional signals (max 30)
    if contact.get("linkedin_url"):
        score += 15
    if not contact.get("is_role"):
        score += 10
    if not contact.get("is_catch_all"):
        score += 5

    return min(score, 100)


async def score_contact_node(state: XmailState) -> dict:
    contacts = state.get("deduplicated_contacts", [])
    scored = [{**c, "confidence_score": _compute_score(c)} for c in contacts]
    # Sort descending — highest confidence first
    scored.sort(key=lambda c: c["confidence_score"], reverse=True)
    logger.info("score_done", contacts=len(scored))
    return {"deduplicated_contacts": scored}
