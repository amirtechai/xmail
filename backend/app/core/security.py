"""Security utilities: brute-force protection, SSRF guard, HTML sanitization."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import bleach

# ── Allowed HTML tags/attrs for campaign bodies ───────────────────────────────

_ALLOWED_TAGS = [
    "a", "b", "blockquote", "br", "code", "div", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "s",
    "span", "strong", "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
]
_ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "style"],
    "td": ["colspan", "rowspan", "align", "valign", "style"],
    "th": ["colspan", "rowspan", "align", "valign", "style"],
    "div": ["style", "class"],
    "span": ["style", "class"],
    "p": ["style"],
    "table": ["width", "cellpadding", "cellspacing", "border", "style"],
}


def sanitize_html(html: str) -> str:
    """Strip disallowed tags/attrs from campaign HTML. Safe against XSS."""
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


# ── SSRF Guard ────────────────────────────────────────────────────────────────

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "169.254.169.254"}


def is_safe_url(url: str) -> bool:
    """Return False if url resolves to a private/internal address (SSRF guard)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        if not host:
            return False
        if host.lower() in _BLOCKED_HOSTNAMES:
            return False
        try:
            addr = ipaddress.ip_address(host)
            if any(addr in net for net in _PRIVATE_NETWORKS):
                return False
        except ValueError:
            # hostname (not IP) — block AWS metadata via hostname too
            if re.match(r"^169\.254\.", host):
                return False
        return True
    except Exception:
        return False


# ── Brute-Force Protection ────────────────────────────────────────────────────

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutes
_ATTEMPT_WINDOW = 600   # 10 minutes sliding window


def _attempt_key(email: str) -> str:
    return f"login_attempts:{email.lower()}"


def _lockout_key(email: str) -> str:
    return f"login_lockout:{email.lower()}"


async def is_account_locked(redis, email: str) -> bool:
    """Return True if the account is currently locked out."""
    return await redis.exists(_lockout_key(email)) == 1


async def record_failed_attempt(redis, email: str) -> int:
    """Increment failed attempt counter. Returns current count."""
    key = _attempt_key(email)
    pipe = redis.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, _ATTEMPT_WINDOW)
    results = await pipe.execute()
    count = results[0]
    if count >= _MAX_ATTEMPTS:
        await redis.setex(_lockout_key(email), _LOCKOUT_SECONDS, "1")
    return count


async def clear_failed_attempts(redis, email: str) -> None:
    """Clear counters after successful login."""
    await redis.delete(_attempt_key(email), _lockout_key(email))
