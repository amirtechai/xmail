"""Unit tests for app.core.auth — JWT helpers and bcrypt password hashing."""

import time

import pytest
from jose import JWTError

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_subject,
    hash_password,
    verify_password,
)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        pw = "S3cur3P@ss!"
        assert hash_password(pw) != pw

    def test_correct_password_verifies(self):
        pw = "S3cur3P@ss!"
        assert verify_password(pw, hash_password(pw)) is True

    def test_wrong_password_fails(self):
        assert verify_password("wrong", hash_password("S3cur3P@ss!")) is False

    def test_different_hashes_for_same_password(self):
        pw = "S3cur3P@ss!"
        assert hash_password(pw) != hash_password(pw)

    def test_empty_password_hashes(self):
        h = hash_password("")
        assert verify_password("", h) is True

    def test_unicode_password(self):
        pw = "pässwörD!123"
        assert verify_password(pw, hash_password(pw)) is True


# ── JWT access token ──────────────────────────────────────────────────────────

class TestAccessToken:
    def test_creates_and_decodes(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_get_subject_returns_sub(self):
        token = create_access_token("user-abc")
        assert get_subject(token) == "user-abc"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_token("not.a.token")

    def test_get_subject_on_invalid_returns_none(self):
        assert get_subject("garbage") is None

    def test_expired_token_raises(self):
        from datetime import timedelta
        token = create_access_token("user-x", expires_delta=timedelta(seconds=-1))
        with pytest.raises(JWTError):
            decode_token(token)


# ── JWT refresh token ─────────────────────────────────────────────────────────

class TestRefreshToken:
    def test_refresh_token_type(self):
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-456"

    def test_access_and_refresh_tokens_differ(self):
        subject = "user-789"
        assert create_access_token(subject) != create_refresh_token(subject)
