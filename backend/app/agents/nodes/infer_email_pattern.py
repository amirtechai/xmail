"""Infer email naming conventions from known contacts, then generate and validate candidates.

Pipeline position: after dedupe_against_db, before score_contact.

Logic:
  1. Group deduplicated contacts by domain.
  2. For each domain with ≥1 matched sample, detect the local-part format
     (first.last, flast, first_last, etc.).
  3. Extract capitalized name pairs from crawled pages for that domain.
  4. Apply the detected format to each extracted name → candidate email.
  5. Validate candidates; merge valid ones into deduplicated_contacts.
"""

import asyncio
import re
from collections import Counter, defaultdict

from app.agents.state import XmailState
from app.core.logger import get_logger

logger = get_logger(__name__)

_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,25})\b")
_MAX_CANDIDATES_PER_DOMAIN = 30
_MAX_CONCURRENT_VALIDATIONS = 10

# Ordered by prevalence in the wild — first match wins during detection
_FORMATS: list[tuple[str, ...]] = [
    ("first.last",  "{fl}.{ll}"),
    ("first_last",  "{fl}_{ll}"),
    ("flast",       "{f}{ll}"),
    ("firstl",      "{fl}{l}"),
    ("f.last",      "{f}.{ll}"),
    ("first.l",     "{fl}.{l}"),
    ("first",       "{fl}"),
    ("last",        "{ll}"),
]


def _render(template: str, first: str, last: str) -> str:
    fl, ll = first.lower(), last.lower()
    return template.format(fl=fl, ll=ll, f=fl[0], l=ll[0])


def _detect_format(local: str, first: str, last: str) -> str | None:
    for fmt, tmpl in _FORMATS:
        if local == _render(tmpl, first, last):
            return fmt
    return None


def _analyze_domain(contacts: list[dict]) -> str | None:
    """Return the dominant format for a domain, or None if uncertain."""
    votes: Counter = Counter()
    for c in contacts:
        name = (c.get("name") or c.get("full_name") or "").strip()
        parts = name.split()
        if len(parts) < 2:
            continue
        first, last = parts[0], parts[-1]
        if "@" not in c.get("email", ""):
            continue
        local = c["email"].split("@")[0]
        fmt = _detect_format(local, first, last)
        if fmt:
            votes[fmt] += 1

    if not votes:
        return None
    top_fmt, top_count = votes.most_common(1)[0]
    # Require at least 1 confirmation, or 2+ if competing formats exist
    if top_count >= 2 or len(votes) == 1:
        return top_fmt
    return None


def _extract_names_from_pages(pages: list[dict], domain: str) -> list[tuple[str, str]]:
    """Extract (First, Last) pairs from pages belonging to the given domain."""
    seen: set[tuple[str, str]] = set()
    names: list[tuple[str, str]] = []
    for page in pages:
        if domain not in page.get("url", ""):
            continue
        for m in _NAME_RE.finditer(page.get("text", "")):
            pair: tuple[str, str] = (m.group(1), m.group(2))
            if pair not in seen:
                seen.add(pair)
                names.append(pair)
    return names[:_MAX_CANDIDATES_PER_DOMAIN]


async def infer_email_pattern_node(state: XmailState) -> dict:
    deduplicated = state.get("deduplicated_contacts", [])
    pages = state.get("crawled_pages", [])
    existing: set[str] = {c["email"].lower() for c in deduplicated if c.get("email")}

    # Group known contacts by domain
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for c in deduplicated:
        email = c.get("email", "")
        if "@" in email:
            by_domain[email.split("@")[1].lower()].append(c)

    candidates: list[tuple[str, dict]] = []  # (email, meta)

    for domain, contacts in by_domain.items():
        fmt_tmpl = dict(_FORMATS).get(_analyze_domain(contacts) or "", "")
        if not fmt_tmpl:
            continue

        for first, last in _extract_names_from_pages(pages, domain):
            email = f"{_render(fmt_tmpl, first, last)}@{domain}"
            if email not in existing:
                existing.add(email)  # prevent duplicates within this loop
                candidates.append((email, {
                    "name": f"{first} {last}",
                    "company": domain,
                    "source_url": f"inferred://{domain}",
                    "inferred": True,
                }))

    if not candidates:
        logger.info("infer_pattern_done", new=0)
        return {}

    from app.email_validator.validator import validate_email

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_VALIDATIONS)

    async def _validate(email: str, meta: dict) -> dict | None:
        async with semaphore:
            try:
                result = await validate_email(email)
            except Exception as exc:
                logger.warning("infer_validate_error", email=email, error=str(exc))
                return None
            if result.status not in ("valid", "catch_all"):
                return None
            return {
                "email": email,
                **meta,
                "verified_status": result.status,
                "validation_score": result.score,
                "mx_valid": result.mx_valid,
                "is_catch_all": result.is_catch_all,
                "is_disposable": False,
                "is_role": False,
                "confidence_score": 0,  # will be set by score_contact_node
            }

    results = await asyncio.gather(*[_validate(e, m) for e, m in candidates])
    valid_new = [r for r in results if r is not None]

    logger.info(
        "infer_pattern_done",
        domains=len(by_domain),
        candidates=len(candidates),
        valid_new=len(valid_new),
    )
    return {
        "deduplicated_contacts": deduplicated + valid_new,
        "inferred_emails": [r["email"] for r in valid_new],
    }
