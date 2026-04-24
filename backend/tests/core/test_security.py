"""Unit tests for app.core.security — HTML sanitization, SSRF guard, brute-force."""

import pytest

from app.core.security import is_safe_url, sanitize_html


# ── sanitize_html ─────────────────────────────────────────────────────────────

class TestSanitizeHtml:
    def test_allows_safe_tags(self):
        html = "<p><strong>Hello</strong> <em>world</em></p>"
        assert sanitize_html(html) == html

    def test_strips_script_tag(self):
        result = sanitize_html("<p>text</p><script>alert(1)</script>")
        # bleach strips tags but preserves text content — script element itself is gone
        assert "<script>" not in result
        assert "</script>" not in result
        assert "<p>text</p>" in result

    def test_strips_onclick_attribute(self):
        result = sanitize_html('<p onclick="evil()">click</p>')
        assert "onclick" not in result
        assert "click" in result

    def test_strips_javascript_href(self):
        result = sanitize_html('<a href="javascript:alert(1)">link</a>')
        assert "javascript:" not in result

    def test_allows_safe_anchor(self):
        html = '<a href="https://example.com" target="_blank">visit</a>'
        result = sanitize_html(html)
        assert 'href="https://example.com"' in result

    def test_allows_img_tag(self):
        html = '<img src="https://example.com/img.png" alt="test">'
        result = sanitize_html(html)
        assert "<img" in result

    def test_empty_string(self):
        assert sanitize_html("") == ""

    def test_plain_text_unchanged(self):
        text = "Hello, world!"
        assert sanitize_html(text) == text

    def test_strips_iframe(self):
        result = sanitize_html('<iframe src="https://evil.com"></iframe>')
        assert "<iframe" not in result

    def test_strips_style_block(self):
        result = sanitize_html('<style>body{display:none}</style><p>ok</p>')
        assert "<style>" not in result
        assert "<p>ok</p>" in result


# ── is_safe_url ───────────────────────────────────────────────────────────────

class TestIsSafeUrl:
    def test_public_https_url_is_safe(self):
        assert is_safe_url("https://example.com/path") is True

    def test_public_http_url_is_safe(self):
        assert is_safe_url("http://example.com") is True

    def test_localhost_is_blocked(self):
        assert is_safe_url("http://localhost:8080/admin") is False

    def test_127_0_0_1_is_blocked(self):
        assert is_safe_url("http://127.0.0.1/secret") is False

    def test_private_10_range_blocked(self):
        assert is_safe_url("http://10.0.0.1/internal") is False

    def test_private_172_range_blocked(self):
        assert is_safe_url("http://172.16.0.1/") is False

    def test_private_192_168_blocked(self):
        assert is_safe_url("http://192.168.1.1/") is False

    def test_aws_metadata_ip_blocked(self):
        assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    def test_aws_metadata_hostname_blocked(self):
        assert is_safe_url("http://metadata.google.internal/") is False

    def test_ftp_scheme_blocked(self):
        assert is_safe_url("ftp://example.com/file") is False

    def test_file_scheme_blocked(self):
        assert is_safe_url("file:///etc/passwd") is False

    def test_empty_string_blocked(self):
        assert is_safe_url("") is False

    def test_no_host_blocked(self):
        assert is_safe_url("https://") is False
