"""LangGraph StateGraph definition — 12-node discovery pipeline."""

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.nodes.crawl_urls import crawl_urls_node
from app.agents.nodes.dedupe_against_db import dedupe_against_db_node
from app.agents.nodes.enrich_contact import enrich_contact_node
from app.agents.nodes.extract_emails import extract_emails_node
from app.agents.nodes.finalize import finalize_node
from app.agents.nodes.hunter_lookup import hunter_lookup_node
from app.agents.nodes.infer_email_pattern import infer_email_pattern_node
from app.agents.nodes.persist_contact import persist_contact_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.rss_feed_reader import rss_feed_reader_node
from app.agents.nodes.score_contact import score_contact_node
from app.agents.nodes.search_web import search_web_node
from app.agents.nodes.validate_email import validate_email_node
from app.agents.state import XmailState


def should_retry(state: XmailState) -> str:
    """Conditional edge: retry planner if no URLs found and retries remain."""
    if not state.get("raw_urls") and state.get("retry_count", 0) < state.get("max_retries", 2):
        return "retry"
    return "continue"


def build_graph(llm_provider, session, redis_client):  # type: ignore[no-untyped-def]
    graph = StateGraph(XmailState)

    # Bind runtime dependencies into nodes
    graph.add_node("planner", partial(planner_node, llm_provider=llm_provider))
    graph.add_node("search_web", search_web_node)
    graph.add_node("crawl_urls", crawl_urls_node)
    graph.add_node("extract_emails", extract_emails_node)
    graph.add_node("enrich_contact", partial(enrich_contact_node, llm_provider=llm_provider))
    graph.add_node("validate_email", validate_email_node)
    graph.add_node("dedupe", partial(dedupe_against_db_node, session=session, redis_client=redis_client))
    graph.add_node("rss_feed_reader", partial(rss_feed_reader_node, session=session))
    graph.add_node("infer_email_pattern", infer_email_pattern_node)
    graph.add_node("hunter_lookup", hunter_lookup_node)
    graph.add_node("score_contact", score_contact_node)
    graph.add_node("persist_contact", partial(persist_contact_node, session=session))
    graph.add_node("finalize", partial(finalize_node, session=session))

    # Linear pipeline with one conditional retry branch
    graph.set_entry_point("planner")
    graph.add_edge("planner", "search_web")
    graph.add_conditional_edges(
        "search_web",
        should_retry,
        {"retry": "planner", "continue": "rss_feed_reader"},
    )
    graph.add_edge("rss_feed_reader", "crawl_urls")
    graph.add_edge("crawl_urls", "extract_emails")
    graph.add_edge("extract_emails", "enrich_contact")
    graph.add_edge("enrich_contact", "validate_email")
    graph.add_edge("validate_email", "dedupe")
    graph.add_edge("dedupe", "infer_email_pattern")
    graph.add_edge("infer_email_pattern", "hunter_lookup")
    graph.add_edge("hunter_lookup", "score_contact")
    graph.add_edge("score_contact", "persist_contact")
    graph.add_edge("persist_contact", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
