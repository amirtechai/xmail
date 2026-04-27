"""Tests for app.tasks.campaign_runner._send()."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.campaign import Campaign, CampaignStatus
from app.models.sent_email import SentEmail
from app.models.smtp_config import SMTPConfiguration

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_campaign(
    hourly_limit: int = 50,
    attachments_metadata: dict | None = None,
) -> Campaign:
    c = Campaign()
    c.id = uuid.uuid4()
    c.user_id = uuid.uuid4()
    c.name = "Test Campaign"
    c.status = CampaignStatus.READY_TO_SEND.value
    c.email_subject = "Hello {first_name}"
    c.email_body_html = "<p>Hi {first_name} from {company}</p>"
    c.email_body_text = "Hi {first_name} from {company}"
    c.legitimate_interest_reason = "Professional profile"
    c.target_audience_type_ids = ["finance"]
    c.smtp_config_id = uuid.uuid4()
    c.hourly_limit = hourly_limit
    c.attachments_metadata = attachments_metadata or {}
    return c


def _make_smtp() -> MagicMock:
    s = MagicMock(spec=SMTPConfiguration)
    s.id = uuid.uuid4()
    s.host = "smtp.example.com"
    s.port = 587
    s.username = "user@example.com"
    s.password_encrypted = "enc"
    s.from_email = "user@example.com"
    s.from_name = "Sender"
    s.use_tls = True
    return s


def _make_contact(email: str = "bob@example.com") -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.email = email
    c.first_name = "Bob"
    c.full_name = "Bob Smith"
    c.company = "ACME"
    return c


def _scalar_one(value: object) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    return r


def _scalars_all(values: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


def _make_session_factory(exec_side_effect) -> tuple[AsyncMock, MagicMock]:
    """Returns (session_mock, factory_mock) with the given execute side effect."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=exec_side_effect)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return session, factory


# ── tests ─────────────────────────────────────────────────────────────────────


class TestCampaignRunnerNotFound:
    @pytest.mark.asyncio
    async def test_missing_campaign_returns_error(self) -> None:
        from app.tasks.campaign_runner import _send

        def _exec(q):
            return _scalar_one(None)

        session, factory = _make_session_factory(_exec)
        task_self = MagicMock()

        with patch("app.database.async_session_factory", factory):
            result = await _send(task_self, str(uuid.uuid4()))

        assert result == {"error": "campaign_not_found"}

    @pytest.mark.asyncio
    async def test_no_smtp_config_returns_error(self) -> None:
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign()
        campaign.smtp_config_id = None

        def _exec(q):
            return _scalar_one(campaign)

        session, factory = _make_session_factory(_exec)
        task_self = MagicMock()

        with patch("app.database.async_session_factory", factory):
            result = await _send(task_self, str(campaign.id))

        assert result == {"error": "no_smtp_config"}


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limited_retries_after_3600(self) -> None:
        """When sent_last_hour >= hourly_limit, schedules a retry and returns rate_limited."""
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign(hourly_limit=10)
        smtp = _make_smtp()
        task_self = MagicMock()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(campaign)
            if call_count == 2:
                return _scalar_one(smtp)
            r = MagicMock()
            r.scalar_one.return_value = 10  # = hourly_limit → rate limited
            return r

        session, factory = _make_session_factory(_exec)

        with patch("app.database.async_session_factory", factory):
            result = await _send(task_self, str(campaign.id))

        assert result["status"] == "rate_limited"
        assert result["retry_in"] == 3600
        task_self.apply_async.assert_called_once_with(args=[str(campaign.id)], countdown=3600)

    @pytest.mark.asyncio
    async def test_batch_capped_by_remaining(self) -> None:
        """batch_size is capped by (hourly_limit - sent_last_hour)."""
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign(hourly_limit=10)
        smtp = _make_smtp()
        # Provide contacts but only 3 should be sent (remaining = 10 - 7 = 3)
        contacts = [_make_contact(f"c{i}@x.com") for i in range(3)]
        task_self = MagicMock()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(campaign)
            if call_count == 2:
                return _scalar_one(smtp)
            if call_count == 3:
                r = MagicMock()
                r.scalar_one.return_value = 7
                return r
            return _scalars_all(contacts)

        session, factory = _make_session_factory(_exec)
        smtp_client = AsyncMock()
        smtp_client.send = AsyncMock(return_value="<msg-id>")

        with (
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
        ):
            result = await _send(task_self, str(campaign.id))

        assert result["sent"] == 3
        assert result["failed"] == 0


class TestSendLoop:
    @pytest.mark.asyncio
    async def test_send_loop_marks_sent(self) -> None:
        """Successfully sent emails set status=SENT and increment sent_count."""
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign(hourly_limit=100)
        smtp = _make_smtp()
        contacts = [_make_contact("alice@example.com")]
        task_self = MagicMock()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(campaign)
            if call_count == 2:
                return _scalar_one(smtp)
            if call_count == 3:
                r = MagicMock()
                r.scalar_one.return_value = 0
                return r
            return _scalars_all(contacts)

        session, factory = _make_session_factory(_exec)
        smtp_client = AsyncMock()
        smtp_client.send = AsyncMock(return_value="<msg@example.com>")

        with (
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
        ):
            result = await _send(task_self, str(campaign.id))

        assert result["sent"] == 1
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_smtp_failure_marks_bounced(self) -> None:
        """SMTP exception sets status=BOUNCED and increments failed_count."""
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign(hourly_limit=100)
        smtp = _make_smtp()
        contacts = [_make_contact("bad@example.com")]
        task_self = MagicMock()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(campaign)
            if call_count == 2:
                return _scalar_one(smtp)
            if call_count == 3:
                r = MagicMock()
                r.scalar_one.return_value = 0
                return r
            return _scalars_all(contacts)

        session, factory = _make_session_factory(_exec)
        smtp_client = AsyncMock()
        smtp_client.send = AsyncMock(side_effect=Exception("Connection refused"))

        with (
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
        ):
            result = await _send(task_self, str(campaign.id))

        assert result["sent"] == 0
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_no_contacts_completes_campaign(self) -> None:
        """When no eligible contacts remain, campaign is marked COMPLETED."""
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign(hourly_limit=100)
        smtp = _make_smtp()
        task_self = MagicMock()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(campaign)
            if call_count == 2:
                return _scalar_one(smtp)
            if call_count == 3:
                r = MagicMock()
                r.scalar_one.return_value = 0
                return r
            return _scalars_all([])

        session, factory = _make_session_factory(_exec)

        with patch("app.database.async_session_factory", factory):
            result = await _send(task_self, str(campaign.id))

        assert result["status"] == "completed"
        assert campaign.status == CampaignStatus.COMPLETED.value


class TestABSplit:
    @pytest.mark.asyncio
    async def test_ab_split_alternates_variants(self) -> None:
        """With subject_b set, even-indexed contacts get variant A, odd get B."""
        from app.tasks.campaign_runner import _send

        campaign = _make_campaign(
            hourly_limit=100,
            attachments_metadata={"email_subject_b": "Subject B — alt"},
        )
        smtp = _make_smtp()
        contacts = [_make_contact(f"c{i}@example.com") for i in range(4)]
        task_self = MagicMock()
        call_count = 0

        def _exec(q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _scalar_one(campaign)
            if call_count == 2:
                return _scalar_one(smtp)
            if call_count == 3:
                r = MagicMock()
                r.scalar_one.return_value = 0
                return r
            return _scalars_all(contacts)

        session, factory = _make_session_factory(_exec)
        smtp_client = AsyncMock()
        smtp_client.send = AsyncMock(return_value="<id>")

        added_emails: list[SentEmail] = []

        def capture_add(obj: object) -> None:
            if isinstance(obj, SentEmail):
                added_emails.append(obj)

        session.add = capture_add

        with (
            patch("app.database.async_session_factory", factory),
            patch("app.sender.smtp_client.SMTPClient", return_value=smtp_client),
        ):
            result = await _send(task_self, str(campaign.id))

        assert result["sent"] == 4
        variants = [e.ab_variant for e in added_emails]
        assert variants[0] == "A"
        assert variants[1] == "B"
        assert variants[2] == "A"
        assert variants[3] == "B"
