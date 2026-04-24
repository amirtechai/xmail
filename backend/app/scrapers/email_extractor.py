"""Standalone email extractor — wraps the agent node logic for use by scrapers."""

from app.agents.nodes.extract_emails import extract_emails_from_text


def extract_from_html(html: str, text: str = "") -> list[str]:
    """Returns deduplicated, filtered email list from page content."""
    combined = html + " " + text
    seen: set[str] = set()
    result: list[str] = []
    for email in extract_emails_from_text(combined):
        if email not in seen:
            seen.add(email)
            result.append(email)
    return result
