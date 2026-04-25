"""Webhook signature verification for SendGrid, Postmark, and Mailgun."""

from __future__ import annotations

import hashlib
import hmac
import base64


def verify_mailgun(timestamp: str, token: str, signature: str, signing_key: str) -> bool:
    """Verify Mailgun webhook HMAC-SHA256 signature."""
    expected = hmac.new(
        signing_key.encode(),
        (timestamp + token).encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_postmark(token_header: str | None, expected_token: str) -> bool:
    """Verify Postmark webhook via shared secret header (X-Postmark-Token)."""
    if not token_header:
        return False
    return hmac.compare_digest(token_header, expected_token)


def verify_sendgrid(raw_body: bytes, signature: str, timestamp: str, public_key_pem: str) -> bool:
    """Verify SendGrid ECDSA P-256 webhook signature.

    SendGrid signs (timestamp_bytes + raw_body) with ECDSA P-256 / SHA-256.
    The public key is the PEM string from the SendGrid dashboard.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        pub_key = load_pem_public_key(public_key_pem.encode())
        sig_bytes = base64.b64decode(signature)
        payload = timestamp.encode() + raw_body
        pub_key.verify(sig_bytes, payload, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False
