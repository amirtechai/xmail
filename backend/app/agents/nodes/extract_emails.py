"""Extract emails node — regex extraction with basic NLP context."""

import re

import bleach

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)

# RFC 5322-simplified pattern — avoids catastrophic backtracking
_EMAIL_RE = re.compile(
    r"(?<![='\"/])"           # not preceded by URL/attr chars
    r"\b([A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,253}\.[A-Za-z]{2,10})\b"
)

_ROLE_PREFIXES = frozenset({
    "info", "admin", "support", "help", "contact", "sales", "hello",
    "team", "office", "webmaster", "postmaster", "noreply", "no-reply",
    "bounce", "abuse", "spam", "marketing", "newsletter",
})

_BLOCKED_DOMAINS = frozenset({
    "example.com", "test.com", "placeholder.com", "yourdomain.com",
    "domain.com", "email.com", "sentry.io", "github.com",
})


def _is_likely_personal(email: str) -> bool:
    local, domain = email.lower().split("@", 1)
    if domain in _BLOCKED_DOMAINS:
        return False
    if local in _ROLE_PREFIXES:
        return False
    # At least one dot or digit in local — filters "name@domain" catch-alls
    return True


def extract_emails_from_text(text: str) -> list[str]:
    # Strip HTML tags safely before regex to avoid extracting partial HTML entities
    clean = bleach.clean(text, tags=[], strip=True)
    found = _EMAIL_RE.findall(clean)
    return [e.lower() for e in found if _is_likely_personal(e)]


async def extract_emails_node(state: XmailState) -> dict:
    pages = state.get("crawled_pages", [])
    existing: set[str] = set(state.get("extracted_emails", []))
    new_emails: list[str] = []

    for page in pages:
        emails = extract_emails_from_text(page.get("html", "") + " " + page.get("text", ""))
        for email in emails:
            if email not in existing:
                existing.add(email)
                new_emails.append(email)

    all_emails = list(state.get("extracted_emails", [])) + new_emails
    logger.info("extract_done", new=len(new_emails), total=len(all_emails))
    return {"extracted_emails": all_emails}
