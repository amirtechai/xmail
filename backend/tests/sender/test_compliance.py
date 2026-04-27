"""Tests for app.sender.compliance — footer injection and suppression logic."""

from __future__ import annotations

from unittest.mock import patch

from app.sender.compliance import (
    build_unsubscribe_url,
    check_suppression_required,
    inject_compliance_footer,
)

# ── build_unsubscribe_url ─────────────────────────────────────────────────────


class TestBuildUnsubscribeUrl:
    def test_url_contains_token(self) -> None:
        with patch("app.sender.compliance.settings") as s:
            s.unsubscribe_base_url = "https://mail.example.com/u"
            url = build_unsubscribe_url("abc123")
        assert url == "https://mail.example.com/u/abc123"

    def test_url_with_uuid_token(self) -> None:
        token = "550e8400-e29b-41d4-a716-446655440000"
        with patch("app.sender.compliance.settings") as s:
            s.unsubscribe_base_url = "https://x.com/u"
            url = build_unsubscribe_url(token)
        assert token in url


# ── inject_compliance_footer ──────────────────────────────────────────────────


class TestInjectComplianceFooter:
    def _settings(self):
        s_mock = patch("app.sender.compliance.settings")
        mock = s_mock.start()
        mock.unsubscribe_base_url = "https://mail.example.com/u"
        mock.tracking_base_url = "https://mail.example.com/t"
        mock.company_physical_address = "123 Main St, London, UK"
        return s_mock

    def test_html_footer_appended(self) -> None:
        p = self._settings()
        try:
            html_out, _ = inject_compliance_footer(
                html_body="<p>Hello</p>",
                text_body="Hello",
                unsubscribe_token="tok1",
            )
        finally:
            p.stop()

        assert "<p>Hello</p>" in html_out
        assert "Unsubscribe" in html_out
        assert "tok1" in html_out

    def test_text_footer_appended(self) -> None:
        p = self._settings()
        try:
            _, text_out = inject_compliance_footer(
                html_body="<p>Hi</p>",
                text_body="Hi there",
                unsubscribe_token="tok2",
            )
        finally:
            p.stop()

        assert "Hi there" in text_out
        assert "tok2" in text_out

    def test_company_address_in_footer(self) -> None:
        p = self._settings()
        try:
            html_out, text_out = inject_compliance_footer(
                html_body="",
                text_body="",
                unsubscribe_token="x",
            )
        finally:
            p.stop()

        assert "123 Main St, London, UK" in html_out
        assert "123 Main St, London, UK" in text_out

    def test_tracking_pixel_included_when_sent_email_id_given(self) -> None:
        p = self._settings()
        try:
            html_out, _ = inject_compliance_footer(
                html_body="<p>Body</p>",
                text_body="Body",
                unsubscribe_token="tok",
                sent_email_id="email-uuid-123",
            )
        finally:
            p.stop()

        assert "email-uuid-123.gif" in html_out
        assert 'width="1"' in html_out

    def test_no_tracking_pixel_when_sent_email_id_absent(self) -> None:
        p = self._settings()
        try:
            html_out, _ = inject_compliance_footer(
                html_body="<p>Body</p>",
                text_body="Body",
                unsubscribe_token="tok",
            )
        finally:
            p.stop()

        assert ".gif" not in html_out

    def test_unsubscribe_link_points_to_correct_url(self) -> None:
        p = self._settings()
        try:
            html_out, _ = inject_compliance_footer(
                html_body="",
                text_body="",
                unsubscribe_token="mytoken",
            )
        finally:
            p.stop()

        assert 'href="https://mail.example.com/u/mytoken"' in html_out


# ── check_suppression_required ────────────────────────────────────────────────


class TestCheckSuppressionRequired:
    def test_complaint_triggers_suppression(self) -> None:
        assert check_suppression_required(bounce_count=0, complaint=True) is True

    def test_two_bounces_triggers_suppression(self) -> None:
        assert check_suppression_required(bounce_count=2, complaint=False) is True

    def test_more_than_two_bounces_triggers_suppression(self) -> None:
        assert check_suppression_required(bounce_count=5, complaint=False) is True

    def test_one_bounce_no_complaint_no_suppression(self) -> None:
        assert check_suppression_required(bounce_count=1, complaint=False) is False

    def test_zero_bounce_no_complaint_no_suppression(self) -> None:
        assert check_suppression_required(bounce_count=0, complaint=False) is False
