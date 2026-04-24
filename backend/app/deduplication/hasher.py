"""Email normalization and SHA256 hashing for deduplication."""

import hashlib
import re


def normalize_email(email: str) -> str:
    """Normalize email to canonical form before hashing.

    Lowercases, strips whitespace, handles Gmail dot-insensitivity
    and plus-addressing for major providers.
    """
    email = email.strip().lower()
    local, _, domain = email.partition("@")

    # Strip plus-addressing (e.g. user+tag@gmail.com → user@gmail.com)
    local = local.split("+")[0]

    # Gmail: dots in local part are ignored
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")

    return f"{local}@{domain}"


def hash_email(email: str) -> str:
    """Return hex SHA256 of the normalized email."""
    normalized = normalize_email(email)
    return hashlib.sha256(normalized.encode()).hexdigest()


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    # Remove www. prefix
    domain = re.sub(r"^www\.", "", domain)
    return domain
