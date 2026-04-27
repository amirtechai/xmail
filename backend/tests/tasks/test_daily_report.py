"""Tests for app.tasks.daily_report_delivery._deliver()."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.daily_report import DailyReport

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_report(
    report_date: date | None = None,
    emails_sent: int = 100,
    emails_opened: int = 30,
    emails_clicked: int = 10,
    emails_bounced: int = 5,
    contacts_discovered: int = 50,
) -> DailyReport:
    r = DailyReport()
    r.id = uuid.uuid4()
    r.report_date = report_date or date(2026, 4, 27)
    r.emails_sent = emails_sent
    r.emails_opened = emails_opened
    r.emails_clicked = emails_clicked
    r.emails_bounced = emails_bounced
    r.contacts_discovered = contacts_discovered
    return r


def _make_smtp() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.host = "smtp.example.com"
    return s


def _scalar_one(value: object) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    return r


def _make_session_factory(exec_side_effect) -> tuple[AsyncMock, MagicMock]:
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=exec_side_effect)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return session, factory


def _fake_settings(admin_email: str = "admin@example.com") -> MagicMock:
    s = MagicMock()
    s.admin_email = admin_email
    return s


def _fake_path(exists: bool = True) -> MagicMock:
    p = MagicMock()
    p.exists.return_value = exists
    return p


# ── tests ─────────────────────────────────────────────────────────────────────


class TestDeliverDailyReport:
    @pytest.mark.asyncio
    async def test_skips_when_no_admin_email_configured(self) -> None:
        from app.tasks.daily_report_delivery import _deliver

        with patch("app.config.settings", _fake_settings(admin_email="")):
            result = await _deliver(date(2026, 4, 27))

        assert result == {"skipped": True}

    @pytest.mark.asyncio
    async def test_error_when_report_not_found(self) -> None:
        from app.tasks.daily_report_delivery import _deliver

        _, factory = _make_session_factory(lambda q: _scalar_one(None))

        with (
            patch("app.config.settings", _fake_settings()),
            patch("app.database.async_session_factory", factory),
        ):
            result = await _deliver(date(2026, 4, 27))

        assert result == {"error": "report_not_found"}

    @pytest.mark.asyncio
    async def test_skips_when_no_admin_users(self) -> None:
        from app.tasks.daily_report_delivery import _deliver

        report = _make_report()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(report)
            r = MagicMock()
            r.fetchall.return_value = []
            return r

        _, factory = _make_session_factory(_exec)

        with (
            patch("app.config.settings", _fake_settings()),
            patch("app.database.async_session_factory", factory),
        ):
            result = await _deliver(date(2026, 4, 27))

        assert result == {"skipped": True}

    @pytest.mark.asyncio
    async def test_open_and_click_rate_calculation(self) -> None:
        """open_rate = 50/200*100 = 25.0, click_rate = 20/200*100 = 10.0."""
        from app.tasks.daily_report_delivery import _deliver

        report = _make_report(emails_sent=200, emails_opened=50, emails_clicked=20)
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(report)
            if call_count == 2:
                r = MagicMock()
                r.fetchall.return_value = [("admin@x.com",)]
                return r
            if call_count == 3:
                r = MagicMock()
                r.scalars.return_value = iter([])
                return r
            return _scalar_one(_make_smtp())

        _, factory = _make_session_factory(_exec)
        smtp_client = AsyncMock()
        smtp_client.send = AsyncMock(return_value="<id>")

        with (
            patch("app.config.settings", _fake_settings()),
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
            patch("app.reports.storage.pdf_path", return_value=_fake_path()),
            patch("app.reports.storage.xml_path", return_value=_fake_path()),
        ):
            result = await _deliver(date(2026, 4, 27))

        assert "admin@x.com" in result["delivered_to"]
        html_body = smtp_client.send.call_args.kwargs.get("html_body", "")
        assert "25.0%" in html_body  # open rate
        assert "10.0%" in html_body  # click rate

    @pytest.mark.asyncio
    async def test_per_recipient_failure_does_not_abort(self) -> None:
        """Failed per-recipient sends are in 'failed'; others still deliver."""
        from app.tasks.daily_report_delivery import _deliver

        report = _make_report()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(report)
            if call_count == 2:
                r = MagicMock()
                r.fetchall.return_value = [("admin1@x.com",), ("admin2@x.com",)]
                return r
            if call_count == 3:
                r = MagicMock()
                r.scalars.return_value = iter([])
                return r
            return _scalar_one(_make_smtp())

        _, factory = _make_session_factory(_exec)

        async def _send_side(**kwargs):
            if kwargs["to_email"] == "admin1@x.com":
                raise Exception("SMTP error")
            return "<msg>"

        smtp_client = AsyncMock()
        smtp_client.send = _send_side

        with (
            patch("app.config.settings", _fake_settings()),
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
            patch("app.reports.storage.pdf_path", return_value=_fake_path()),
            patch("app.reports.storage.xml_path", return_value=_fake_path()),
        ):
            result = await _deliver(date(2026, 4, 27))

        assert "admin1@x.com" in result["failed"]
        assert "admin2@x.com" in result["delivered_to"]

    @pytest.mark.asyncio
    async def test_zero_sent_gives_zero_rates(self) -> None:
        """Division-by-zero guard: rates are 0.0 when emails_sent == 0."""
        from app.tasks.daily_report_delivery import _deliver

        report = _make_report(emails_sent=0, emails_opened=0, emails_clicked=0)
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(report)
            if call_count == 2:
                r = MagicMock()
                r.fetchall.return_value = [("admin@x.com",)]
                return r
            if call_count == 3:
                r = MagicMock()
                r.scalars.return_value = iter([])
                return r
            return _scalar_one(_make_smtp())

        _, factory = _make_session_factory(_exec)
        smtp_client = AsyncMock()
        smtp_client.send = AsyncMock(return_value="<id>")

        with (
            patch("app.config.settings", _fake_settings()),
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
            patch("app.reports.storage.pdf_path", return_value=_fake_path()),
            patch("app.reports.storage.xml_path", return_value=_fake_path()),
        ):
            await _deliver(date(2026, 4, 27))

        html_body = smtp_client.send.call_args.kwargs.get("html_body", "")
        assert "0.0%" in html_body
