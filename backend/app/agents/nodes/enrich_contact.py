"""Enrich contact node — LLM extracts name/company/title from surrounding page text."""

import json

from app.agents.state import XmailState
from app.core.logger import get_logger
from app.llm.base import LLMMessage

logger = get_logger(__name__)

_SYSTEM = """You are a data extraction assistant.
Given a list of emails found on a webpage, extract structured contact info.
Return a JSON array where each element has: email, name (or null), company (or null), title (or null), linkedin_url (or null).
Use only information explicitly present in the context. Do not fabricate data.
Return ONLY valid JSON — no explanation."""

_MAX_BATCH = 20  # emails per LLM call to stay within token limits


def _build_context(emails: list[str], pages: list[dict]) -> str:
    """Find page snippets that contain each email."""
    snippets: list[str] = []
    email_set = set(emails)
    for page in pages:
        text = page.get("text", "")
        for email in email_set:
            idx = text.lower().find(email.lower())
            if idx != -1:
                start = max(0, idx - 300)
                end = min(len(text), idx + 300)
                snippets.append(f"[{page['url']}]\n{text[start:end]}")
    return "\n\n---\n\n".join(snippets[:10])  # cap context size


async def enrich_contact_node(state: XmailState, llm_provider) -> dict:  # type: ignore[no-untyped-def]
    emails = state.get("extracted_emails", [])
    pages = state.get("crawled_pages", [])
    already_enriched = {c["email"] for c in state.get("enriched_contacts", [])}
    to_enrich = [e for e in emails if e not in already_enriched]

    enriched = list(state.get("enriched_contacts", []))

    for i in range(0, len(to_enrich), _MAX_BATCH):
        batch = to_enrich[i : i + _MAX_BATCH]
        context = _build_context(batch, pages)
        messages = [
            LLMMessage(role="system", content=_SYSTEM),
            LLMMessage(
                role="user",
                content=f"Emails: {json.dumps(batch)}\n\nContext:\n{context[:3000]}",
            ),
        ]
        try:
            response = await llm_provider.complete(messages, temperature=0.1, max_tokens=2000)
            contacts = json.loads(response.content)
            if isinstance(contacts, list):
                enriched.extend(contacts)
        except Exception as exc:
            logger.warning("enrich_batch_failed", reason=str(exc))
            # Fallback: bare contact records with just email
            enriched.extend({"email": e, "name": None, "company": None, "title": None, "linkedin_url": None} for e in batch)

    logger.info("enrich_done", total=len(enriched))
    return {"enriched_contacts": enriched}
