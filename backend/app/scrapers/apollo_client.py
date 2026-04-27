"""Apollo.io REST API client — people search for targeted contact discovery."""

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.apollo.io/v1"

# Finance industry tag IDs from Apollo taxonomy
FINANCE_INDUSTRY_TAGS = [
    "5567d4096163641a56000001",  # Finance
    "5567d4096163641a56000002",  # Financial Services
    "5567d4096163641a56000003",  # Investment Banking
    "5567d4096163641a56000004",  # Investment Management
    "5567d4096163641a56000005",  # Capital Markets
    "5567d4096163641a56000006",  # Private Equity
    "5567d4096163641a56000007",  # Venture Capital
    "5567d4096163641a56000008",  # Hedge Funds
    "5567d4096163641a56000009",  # Asset Management
]

FINANCE_TITLES = [
    "CFO",
    "Chief Financial Officer",
    "Portfolio Manager",
    "Managing Director",
    "Investment Manager",
    "Fund Manager",
    "VP Finance",
    "VP of Finance",
    "Director of Finance",
    "Head of Finance",
    "Private Equity",
    "Hedge Fund",
    "Investment Analyst",
    "Senior Analyst",
    "Research Analyst",
    "CFA",
    "Treasurer",
    "Controller",
    "Chief Investment Officer",
    "CIO",
    "Head of Investments",
]

FINANCE_SENIORITIES = ["vp", "director", "c_suite", "partner", "manager", "senior"]


@dataclass
class ApolloPerson:
    email: str
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    country: str | None = None
    email_status: str = "unknown"
    seniority: str | None = None
    departments: list[str] = field(default_factory=list)


class ApolloClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def people_search(
        self,
        titles: list[str] | None = None,
        industry_tags: list[str] | None = None,
        seniorities: list[str] | None = None,
        keywords: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> list[ApolloPerson]:
        payload: dict = {
            "api_key": self._api_key,
            "page": page,
            "per_page": per_page,
            "contact_email_status": ["verified", "likely to engage"],
        }
        if titles:
            payload["person_titles"] = titles
        if industry_tags:
            payload["q_organization_industry_tag_ids"] = industry_tags
        if seniorities:
            payload["person_seniorities"] = seniorities
        if keywords:
            payload["q_keywords"] = " ".join(keywords)

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{_BASE}/mixed_people/search",
                json=payload,
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            )
            r.raise_for_status()

        return self._parse_response(r.json())

    async def finance_people_search(
        self,
        keywords: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> list[ApolloPerson]:
        return await self.people_search(
            titles=FINANCE_TITLES,
            industry_tags=FINANCE_INDUSTRY_TAGS,
            seniorities=FINANCE_SENIORITIES,
            keywords=keywords,
            page=page,
            per_page=per_page,
        )

    def _parse_response(self, data: dict) -> list[ApolloPerson]:
        people = []
        for p in data.get("people", []) + data.get("contacts", []):
            email = (
                p.get("email")
                or (p.get("contact", {}) or {}).get("email")
            )
            if not email or "@" not in email:
                continue
            org = p.get("organization") or p.get("employment_history", [{}])[0] if p.get("employment_history") else {}
            people.append(ApolloPerson(
                email=email.lower().strip(),
                first_name=p.get("first_name"),
                last_name=p.get("last_name"),
                title=p.get("title"),
                company=p.get("organization_name") or (org.get("name") if isinstance(org, dict) else None),
                company_domain=p.get("organization", {}).get("primary_domain") if isinstance(p.get("organization"), dict) else None,
                linkedin_url=p.get("linkedin_url"),
                city=p.get("city"),
                country=p.get("country"),
                email_status=p.get("email_status", "unknown"),
                seniority=p.get("seniority"),
                departments=p.get("departments", []),
            ))
        return people
