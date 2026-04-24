"""Spam score analysis via Postmark's free spamcheck API."""

import email.mime.multipart
import email.mime.text
from dataclasses import dataclass

import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)

_POSTMARK_URL = "https://spamcheck.postmarkapp.com/filter"
_TIMEOUT = 10.0


@dataclass
class SpamRule:
    name: str
    description: str
    score: float


@dataclass
class SpamResult:
    score: float
    rules: list[SpamRule]

    @property
    def label(self) -> str:
        if self.score < 2.0:
            return "good"
        if self.score < 4.0:
            return "fair"
        if self.score < 6.0:
            return "warning"
        return "high_risk"


def _build_rfc2822(subject: str, html_body: str, text_body: str, from_email: str) -> str:
    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = "test@example.com"
    msg.attach(email.mime.text.MIMEText(text_body or "", "plain", "utf-8"))
    msg.attach(email.mime.text.MIMEText(html_body or "", "html", "utf-8"))
    return msg.as_string()


async def check_spam(
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str = "outreach@example.com",
) -> SpamResult:
    raw = _build_rfc2822(subject, html_body, text_body, from_email)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _POSTMARK_URL,
            json={"email": raw, "options": "long"},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("success"):
        logger.warning("spamcheck_failed", response=data)
        return SpamResult(score=0.0, rules=[])

    rules = [
        SpamRule(
            name=r.get("name", ""),
            description=r.get("description", ""),
            score=float(r.get("score", 0)),
        )
        for r in data.get("rules", [])
    ]
    return SpamResult(score=float(data.get("score", 0)), rules=rules)
