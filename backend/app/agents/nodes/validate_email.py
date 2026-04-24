"""Validate email node — delegates to the 4-stage email validator pipeline."""

import asyncio

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)

_MAX_CONCURRENT = 10


async def _validate_one(contact: dict) -> dict:
    """Runs all 4 validation stages and returns contact with status/score."""
    from app.email_validator.validator import validate_email

    email = contact.get("email", "")
    result = await validate_email(email)
    return {
        **contact,
        "verified_status": result.status,
        "validation_score": result.score,
        "mx_valid": result.mx_valid,
        "is_catch_all": result.is_catch_all,
        "is_disposable": result.is_disposable,
        "is_role": result.is_role,
    }


async def validate_email_node(state: XmailState) -> dict:
    contacts = state.get("enriched_contacts", [])
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def bounded(c: dict) -> dict:
        async with semaphore:
            return await _validate_one(c)

    validated = await asyncio.gather(*[bounded(c) for c in contacts])
    # Keep only valid/risky — discard hard invalids to save DB space
    kept = [c for c in validated if c.get("verified_status") not in ("invalid", "disposable")]
    logger.info("validate_done", total=len(contacts), kept=len(kept))
    return {"validated_contacts": list(kept)}
