"""Disposable email address (DEA) domain check."""

# Common disposable email providers — extend as needed
_DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "tempmail.com",
        "throwam.com",
        "yopmail.com",
        "sharklasers.com",
        "guerrillamailblock.com",
        "grr.la",
        "guerrillamail.info",
        "guerrillamail.biz",
        "guerrillamail.de",
        "guerrillamail.net",
        "guerrillamail.org",
        "spam4.me",
        "trashmail.com",
        "trashmail.me",
        "trashmail.net",
        "dispostable.com",
        "maildrop.cc",
        "10minutemail.com",
        "10minutemail.net",
        "fakeinbox.com",
        "mailnull.com",
        "spamgourmet.com",
        "spamgourmet.net",
        "spamgourmet.org",
        "deadaddress.com",
        "spamex.com",
        "mailexpire.com",
        "spamfree24.org",
        "spam.la",
        "spamhole.com",
        "spamoff.de",
        "spamspot.com",
        "spamstack.net",
        "throwaway.email",
        "tempinbox.com",
        "emailondeck.com",
    }
)


def is_disposable(email: str) -> bool:
    domain = email.split("@")[-1].lower()
    return domain in _DISPOSABLE_DOMAINS
