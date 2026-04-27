"""Unit tests for app.core.webhook_signatures."""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac

import pytest

# ── verify_mailgun ────────────────────────────────────────────────────────────

class TestVerifyMailgun:
    from app.core.webhook_signatures import verify_mailgun

    def _sign(self, timestamp: str, token: str, key: str) -> str:
        return _hmac.new(key.encode(), (timestamp + token).encode(), hashlib.sha256).hexdigest()

    def test_valid_signature(self):
        from app.core.webhook_signatures import verify_mailgun
        ts, tok, key = "1714000000", "abc123xyz", "secret-key"
        sig = self._sign(ts, tok, key)
        assert verify_mailgun(ts, tok, sig, key) is True

    def test_wrong_key(self):
        from app.core.webhook_signatures import verify_mailgun
        ts, tok = "1714000000", "abc123xyz"
        sig = self._sign(ts, tok, "correct-key")
        assert verify_mailgun(ts, tok, sig, "wrong-key") is False

    def test_tampered_timestamp(self):
        from app.core.webhook_signatures import verify_mailgun
        ts, tok, key = "1714000000", "token", "k"
        sig = self._sign(ts, tok, key)
        assert verify_mailgun("9999999999", tok, sig, key) is False

    def test_tampered_token(self):
        from app.core.webhook_signatures import verify_mailgun
        ts, tok, key = "1714000000", "token", "k"
        sig = self._sign(ts, tok, key)
        assert verify_mailgun(ts, "other-token", sig, key) is False

    def test_empty_signature(self):
        from app.core.webhook_signatures import verify_mailgun
        assert verify_mailgun("ts", "tok", "", "key") is False


# ── verify_postmark ───────────────────────────────────────────────────────────

class TestVerifyPostmark:
    def test_valid_token(self):
        from app.core.webhook_signatures import verify_postmark
        assert verify_postmark("my-secret", "my-secret") is True

    def test_wrong_token(self):
        from app.core.webhook_signatures import verify_postmark
        assert verify_postmark("wrong", "my-secret") is False

    def test_none_header(self):
        from app.core.webhook_signatures import verify_postmark
        assert verify_postmark(None, "my-secret") is False

    def test_empty_header(self):
        from app.core.webhook_signatures import verify_postmark
        assert verify_postmark("", "my-secret") is False

    def test_case_sensitive(self):
        from app.core.webhook_signatures import verify_postmark
        assert verify_postmark("My-Secret", "my-secret") is False


# ── verify_sendgrid ───────────────────────────────────────────────────────────

class TestVerifySendgrid:
    @pytest.fixture(scope="class")
    def ec_keypair(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key_pem = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
        return private_key, public_key_pem

    def _make_sig(self, private_key, timestamp: str, body: bytes) -> str:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        payload = timestamp.encode() + body
        sig = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(sig).decode()

    def test_valid_signature(self, ec_keypair):
        from app.core.webhook_signatures import verify_sendgrid
        priv, pub_pem = ec_keypair
        body = b'[{"event":"open"}]'
        ts = "1714000000"
        sig = self._make_sig(priv, ts, body)
        assert verify_sendgrid(body, sig, ts, pub_pem) is True

    def test_wrong_key(self, ec_keypair):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        from app.core.webhook_signatures import verify_sendgrid
        priv, _ = ec_keypair
        body = b'[{"event":"open"}]'
        ts = "1714000000"
        sig = self._make_sig(priv, ts, body)
        # different key pair
        other_pub = ec.generate_private_key(ec.SECP256R1()).public_key()
        other_pem = other_pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
        assert verify_sendgrid(body, sig, ts, other_pem) is False

    def test_tampered_body(self, ec_keypair):
        from app.core.webhook_signatures import verify_sendgrid
        priv, pub_pem = ec_keypair
        body = b'[{"event":"open"}]'
        ts = "1714000000"
        sig = self._make_sig(priv, ts, body)
        assert verify_sendgrid(b'tampered', sig, ts, pub_pem) is False

    def test_invalid_base64_signature(self, ec_keypair):
        from app.core.webhook_signatures import verify_sendgrid
        _, pub_pem = ec_keypair
        assert verify_sendgrid(b'body', "not-valid-base64!!!!", "ts", pub_pem) is False

    def test_invalid_pem(self):
        from app.core.webhook_signatures import verify_sendgrid
        assert verify_sendgrid(b'body', base64.b64encode(b'x').decode(), "ts", "not-a-pem") is False
