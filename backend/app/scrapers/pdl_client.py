"""People Data Labs (PDL) API client — person enrichment."""

from dataclasses import dataclass, field

import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)

_BASE = "https://api.peopledatalabs.com/v5"


@dataclass
class PDLPerson:
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    country: str | None = None
    city: str | None = None
    industry: str | None = None
    job_company_industry: str | None = None
    seniority: str | None = None
    departments: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    likelihood: int = 0


class PDLClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    async def enrich_by_email(self, email: str) -> PDLPerson | None:
        params: dict[str, str | int | bool] = {"email": email, "pretty": False, "titlecase": False}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_BASE}/person/enrich",
                headers=self._headers,
                params=params,
            )
        if r.status_code == 404:
            return None
        if r.status_code == 402:
            logger.warning("pdl_quota_exceeded")
            return None
        r.raise_for_status()
        return self._parse(r.json())

    async def enrich_by_name_company(
        self, first_name: str, last_name: str, company: str
    ) -> PDLPerson | None:
        payload = {
            "params": {
                "profile": [f"linkedin.com/in/{first_name.lower()}-{last_name.lower()}"],
                "first_name": first_name,
                "last_name": last_name,
                "company": company,
            },
            "required": "emails",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{_BASE}/person/identify",
                headers=self._headers,
                json=payload,
            )
        if r.status_code in (404, 400):
            return None
        if r.status_code == 402:
            logger.warning("pdl_quota_exceeded")
            return None
        r.raise_for_status()
        data = r.json()
        matches = data.get("matches", [])
        if not matches:
            return None
        return self._parse(matches[0])

    def _parse(self, data: dict) -> PDLPerson:
        emails = data.get("emails", [])
        primary_email = next(
            (e["address"] for e in emails if e.get("type") == "professional"),
            emails[0]["address"] if emails else None,
        )
        linkedin = next(
            (p for p in data.get("profiles", []) if "linkedin" in p.lower()),
            None,
        )
        exp = (data.get("experience") or [{}])[0]
        return PDLPerson(
            email=primary_email,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            full_name=data.get("full_name"),
            title=data.get("job_title") or exp.get("title", {}).get("name"),
            company=data.get("job_company_name") or exp.get("company", {}).get("name"),
            linkedin_url=linkedin,
            twitter_url=next((p for p in data.get("profiles", []) if "twitter" in p.lower()), None),
            country=data.get("location_country"),
            city=data.get("location_locality"),
            industry=data.get("industry"),
            job_company_industry=data.get("job_company_industry"),
            seniority=data.get("job_title_levels", [None])[0],
            departments=data.get("job_title_role", []) or [],
            skills=[s.get("name", "") for s in (data.get("skills") or [])[:15]],
            education=[
                {
                    "school": e.get("school", {}).get("name"),
                    "degree": e.get("degrees", [None])[0],
                    "end_year": (e.get("end_date") or "")[:4] or None,
                }
                for e in (data.get("education") or [])[:3]
            ],
            likelihood=data.get("likelihood", 0),
        )
