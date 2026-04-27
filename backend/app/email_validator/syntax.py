"""RFC 5322 email syntax validation."""

import re

# Stricter than the agent extraction regex — used for definitive validation
_VALID_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,253}\.[A-Za-z]{2,10}$")


def is_valid_syntax(email: str) -> bool:
    if not email or len(email) > 320:
        return False
    if email.count("@") != 1:
        return False
    local, domain = email.split("@", 1)
    if local.startswith(".") or local.endswith("."):
        return False
    if ".." in local or ".." in domain:
        return False
    return bool(_VALID_EMAIL.match(email))
