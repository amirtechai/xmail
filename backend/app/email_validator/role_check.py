"""Role-based email address detection."""

_ROLE_LOCALS: frozenset[str] = frozenset(
    {
        "info",
        "admin",
        "support",
        "help",
        "contact",
        "sales",
        "hello",
        "team",
        "office",
        "webmaster",
        "postmaster",
        "noreply",
        "no-reply",
        "bounce",
        "abuse",
        "spam",
        "marketing",
        "newsletter",
        "billing",
        "accounts",
        "hr",
        "jobs",
        "careers",
        "press",
        "media",
        "legal",
        "privacy",
        "security",
        "compliance",
        "service",
        "services",
        "customerservice",
        "feedback",
        "enquiries",
        "enquiry",
        "inquiry",
        "inquiries",
    }
)


def is_role_address(email: str) -> bool:
    local = email.split("@")[0].lower().rstrip("+0123456789")
    return local in _ROLE_LOCALS
