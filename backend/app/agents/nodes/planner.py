"""Planner node — LLM generates targeted search queries for the audience type."""

from app.agents.state import XmailState
from app.core.logger import get_logger
from app.llm.base import LLMMessage

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a B2B lead generation specialist.
Generate targeted Google search queries to find {audience_type} professionals with public email addresses.
Return ONLY a JSON array of strings — no explanation.
Example: ["site:linkedin.com {audience_type} email contact", ...]
Generate exactly {count} diverse queries covering different angles (directories, associations, news mentions, company pages)."""


async def planner_node(state: XmailState, llm_provider) -> dict:  # type: ignore[no-untyped-def]
    audience = state["audience_type"]
    keywords = ", ".join(state["audience_keywords"][:10])
    count = min(state["target_count"] // 5, 20)  # 5 results per query estimate

    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT.format(audience_type=audience, count=count)),
        LLMMessage(role="user", content=f"Keywords: {keywords}\nGenerate {count} queries."),
    ]

    try:
        response = await llm_provider.complete(messages, temperature=0.4, max_tokens=1000)
        import json
        queries = json.loads(response.content)
        if not isinstance(queries, list):
            raise ValueError("Expected a JSON array")
        logger.info("planner_done", query_count=len(queries), audience=audience)
        return {"search_queries": queries[:count]}
    except Exception as exc:
        logger.error("planner_error", error=str(exc))
        # Fallback: keyword-based queries
        fallback = [
            f'"{audience}" email contact site:linkedin.com',
            f'"{audience}" directory "email" filetype:html',
            f'"{keywords}" "{audience}" contact email',
        ]
        return {"search_queries": fallback, "error": str(exc)}
