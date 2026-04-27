"""Hunter.io REST API client — domain_search and email_finder."""

from dataclasses import dataclass

import httpx

from app.core.logger import get_logger
logger = get_logger(__name__)

_BASE = "https://api.hunter.io/v2"


@dataclass
class HunterEmail:
    email: str
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    linkedin_url: str | None = None
    confidence: int = 0


@dataclass
class HunterFinderResult:
    email: str | None
    score: int = 0
    first_name: str | None = None
    last_name: str | None = None


class HunterClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def domain_search(self, domain: str, limit: int = 100) -> list[HunterEmail]:
        params = {"domain": domain, "limit": limit, "api_key": self._api_key}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{_BASE}/domain-search", params=params)
            r.raise_for_status()
        results = []
        for item in r.json().get("data", {}).get("emails", []):
            results.append(HunterEmail(
                email=item["value"],
                first_name=item.get("first_name"),
                last_name=item.get("last_name"),
                position=item.get("position"),
                linkedin_url=item.get("linkedin"),
                confidence=item.get("confidence", 0),
            ))
        return results

    async def email_finder(self, domain: str, first_name: str, last_name: str) -> HunterFinderResult:
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self._api_key,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{_BASE}/email-finder", params=params)
            r.raise_for_status()
        data = r.json().get("data", {})
        return HunterFinderResult(
            email=data.get("email"),
            score=data.get("score", 0),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
        )
