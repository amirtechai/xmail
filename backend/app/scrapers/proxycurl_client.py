"""Proxycurl API client — LinkedIn profile enrichment."""

import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)

_API_URL = "https://nubela.co/proxycurl/api/v2/linkedin"


async def fetch_linkedin_profile(linkedin_url: str, api_key: str) -> dict | None:
    """
    Fetch LinkedIn profile data from Proxycurl.
    Returns None if profile not found (404) or URL is invalid.
    Raises httpx.HTTPStatusError for other API errors.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            _API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"linkedin_profile_url": linkedin_url, "use_cache": "if-present"},
        )
        if resp.status_code == 404:
            logger.debug("proxycurl_profile_not_found", url=linkedin_url)
            return None
        resp.raise_for_status()
        return resp.json()


def extract_fields(profile: dict) -> dict:
    """Map Proxycurl response to DiscoveredContact field names."""
    current_exp = next(
        (e for e in (profile.get("experiences") or []) if e.get("ends_at") is None),
        None,
    )
    company = (
        (current_exp or {}).get("company")
        or (profile.get("experiences") or [{}])[0].get("company")
        or None
    )
    title = (current_exp or {}).get("title") or profile.get("occupation") or None
    return {
        "first_name": profile.get("first_name") or None,
        "last_name": profile.get("last_name") or None,
        "full_name": profile.get("full_name") or None,
        "title": title,
        "company": company,
        "country": profile.get("country") or None,
        "twitter_handle": profile.get("twitter_handle") or None,
    }
