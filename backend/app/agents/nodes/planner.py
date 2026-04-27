"""Planner node — LLM generates targeted search queries for the audience type."""

import json

from app.agents.state import XmailState
from app.core.logger import get_logger
from app.llm.base import LLMMessage

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a B2B lead generation specialist.
Generate targeted Google search queries to find {audience_type} professionals with public email addresses.
Return ONLY a JSON array of strings — no explanation.
Example: ["site:linkedin.com {audience_type} email contact", ...]
Generate exactly {count} diverse queries covering different angles (directories, associations, news mentions, company pages)."""

_FINANCE_SYSTEM_PROMPT = """You are a financial services lead generation specialist.
Generate targeted Google search queries to find finance professionals with public email addresses.
Target roles: Portfolio Manager, Managing Director, CFO, CFA, Investment Analyst, Hedge Fund Manager, PE Analyst, VP Finance, Chief Investment Officer.
Target firms: investment banks, hedge funds, private equity, asset managers, family offices, pension funds.
Return ONLY a JSON array of strings — no explanation.
Generate exactly {count} diverse queries using these angles:
- CFA Institute member directories
- Investment firm "Our Team" pages with emails
- SEC EDGAR contact filings
- Financial conference speaker lists
- Bloomberg/Reuters executive profiles
- Association directories (SIFMA, AIMA, MFA, CFA Society)
- LinkedIn finance executive profiles with email
- Fund administrator databases"""

_FINANCE_FALLBACK_QUERIES = [
    'site:linkedin.com/in "portfolio manager" "email" finance',
    'site:bloomberg.com "managing director" "contact" email',
    '"hedge fund" "portfolio manager" email contact directory',
    '"private equity" "managing director" email site:linkedin.com',
    'CFA "investment analyst" email contact filetype:pdf',
    '"asset management" "director" "email" site:linkedin.com',
    'site:sec.gov "chief financial officer" email contact',
    '"investment banking" "vice president" email directory',
    'AIMA "hedge fund" member directory contact email',
    '"family office" "chief investment officer" email contact',
]


def _is_finance(state: XmailState) -> bool:
    vertical = state.get("industry_vertical", "").lower()
    if vertical == "finance":
        return True
    audience = state.get("audience_type", "").lower()
    keywords = " ".join(state.get("audience_keywords", [])).lower()
    finance_signals = {"finance", "finans", "hedge", "equity", "investment", "banker", "fund", "cfa", "portfolio"}
    return bool(finance_signals & set((audience + " " + keywords).split()))


async def planner_node(state: XmailState, llm_provider) -> dict:  # type: ignore[no-untyped-def]
    audience = state["audience_type"]
    keywords = ", ".join(state["audience_keywords"][:10])
    count = min(state["target_count"] // 5, 20)
    is_finance = _is_finance(state)

    system_prompt = (
        _FINANCE_SYSTEM_PROMPT.format(count=count)
        if is_finance
        else _SYSTEM_PROMPT.format(audience_type=audience, count=count)
    )
    user_msg = f"Keywords: {keywords}\nGenerate {count} queries."
    if is_finance:
        user_msg = f"Focus on finance professionals. Keywords: {keywords}\nGenerate {count} queries."

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_msg),
    ]

    try:
        response = await llm_provider.complete(messages, temperature=0.4, max_tokens=1000)
        queries = json.loads(response.content)
        if not isinstance(queries, list):
            raise ValueError("Expected a JSON array")
        logger.info("planner_done", query_count=len(queries), audience=audience, finance=is_finance)
        return {"search_queries": queries[:count]}
    except Exception as exc:
        logger.error("planner_error", reason=str(exc))
        if is_finance:
            return {"search_queries": _FINANCE_FALLBACK_QUERIES[:count], "error": str(exc)}
        fallback = [
            f'"{audience}" email contact site:linkedin.com',
            f'"{audience}" directory "email" filetype:html',
            f'"{keywords}" "{audience}" contact email',
        ]
        return {"search_queries": fallback, "error": str(exc)}
