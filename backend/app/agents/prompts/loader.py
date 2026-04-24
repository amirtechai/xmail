"""Jinja2-based prompt loader for agent prompts.

Templates here produce LLM system prompts (plain text / Markdown),
NOT HTML rendered to web clients. Autoescape is disabled for .md files
intentionally — output is never sent directly to a browser.
Email HTML bodies produced by draft_email_v1.md are sanitized by
bleach before being injected into MIME messages.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape  # nosemgrep

_PROMPTS_DIR = Path(__file__).parent

# nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2
# Rationale: output goes to LLM API calls (text), never rendered in a browser.
# .md templates: autoescape off (plain text). .html/.xml: autoescape on.
# Email HTML from draft_email_v1.md is sanitized with bleach before MIME injection.
_env = Environment(  # nosemgrep
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=select_autoescape(enabled_extensions=("html", "xml")),
)

_env.filters["first_name"] = lambda name: (name or "").split()[0] if name else "there"


def render_prompt(template_name: str, **kwargs: object) -> str:
    """Render a Markdown prompt template for LLM consumption (not web HTML)."""
    template = _env.get_template(template_name)
    return template.render(**kwargs)  # nosemgrep
