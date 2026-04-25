"""Campaign send task — batched delivery with optional A/B split."""

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.campaign_runner.send_campaign", bind=True)
def send_campaign(self, campaign_id: str) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_send(campaign_id))


async def _send(campaign_id: str) -> dict:
    import hashlib
    import uuid as _uuid

    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.discovered_contact import DiscoveredContact, VerifiedStatus
    from app.models.sent_email import SentEmail, SentEmailStatus
    from app.models.smtp_config import SMTPConfiguration
    from app.sender.smtp_client import SMTPClient

    sent_count = 0
    failed_count = 0

    async with async_session_factory() as session:
        # Load campaign
        campaign = (await session.execute(
            select(Campaign).where(Campaign.id == _uuid.UUID(campaign_id))
        )).scalar_one_or_none()

        if not campaign:
            logger.warning("send_campaign_not_found", campaign_id=campaign_id)
            return {"error": "campaign_not_found"}

        if not campaign.smtp_config_id:
            logger.warning("send_campaign_no_smtp", campaign_id=campaign_id)
            return {"error": "no_smtp_config"}

        smtp = (await session.execute(
            select(SMTPConfiguration).where(SMTPConfiguration.id == campaign.smtp_config_id)
        )).scalar_one_or_none()

        if not smtp:
            return {"error": "smtp_config_not_found"}

        meta = campaign.attachments_metadata or {}
        subject_b: str | None = meta.get("email_subject_b")
        batch_size: int = int(meta.get("batch_size_per_hour") or 50)

        # Find contacts matching campaign audience types, excluding already-sent
        audience_keys = campaign.target_audience_type_ids or []
        already_sent_subq = (
            select(SentEmail.contact_id)
            .where(SentEmail.campaign_id == campaign.id)
            .where(SentEmail.contact_id.is_not(None))
            .scalar_subquery()
        )
        contacts_q = (
            select(DiscoveredContact)
            .where(DiscoveredContact.audience_type_key.in_(audience_keys))
            .where(DiscoveredContact.verified_status.in_([
                VerifiedStatus.VALID.value,
                VerifiedStatus.CATCH_ALL.value,
            ]))
            .where(DiscoveredContact.id.not_in(already_sent_subq))
            .limit(batch_size)
        )
        contacts = (await session.execute(contacts_q)).scalars().all()

        if not contacts:
            campaign.status = CampaignStatus.COMPLETED.value
            await session.commit()
            logger.info("send_campaign_no_contacts", campaign_id=campaign_id)
            return {"sent": 0, "failed": 0, "status": "completed"}

        campaign.status = CampaignStatus.SENDING.value
        await session.commit()

        client = SMTPClient(smtp)
        body_html = campaign.email_body_html or f"<p>{campaign.email_body_text}</p>"
        body_text = campaign.email_body_text or ""

        for idx, contact in enumerate(contacts):
            variant = "B" if (subject_b and idx % 2 == 1) else "A"
            subject = subject_b if variant == "B" else campaign.email_subject

            first_name = contact.first_name or contact.full_name or "there"
            company_name = contact.company or ""

            def interpolate(t: str) -> str:
                return (
                    t.replace("{first_name}", first_name)
                     .replace("{company}", company_name)
                )

            token = str(_uuid.uuid4())
            body_hash = hashlib.sha256(body_html.encode()).hexdigest()

            sent_email = SentEmail(
                campaign_id=campaign.id,
                contact_id=contact.id,
                smtp_config_id=smtp.id,
                subject=interpolate(subject),
                body_hash=body_hash,
                status=SentEmailStatus.QUEUED.value,
                ab_variant=variant if subject_b else None,
            )
            session.add(sent_email)
            await session.flush()

            try:
                msg_id = await client.send(
                    to_email=contact.email,
                    subject=interpolate(subject),
                    html_body=interpolate(body_html),
                    text_body=interpolate(body_text),
                    unsubscribe_token=str(sent_email.id),
                )
                sent_email.status = SentEmailStatus.SENT.value
                sent_email.message_id = msg_id
                from datetime import datetime
                sent_email.sent_at = datetime.utcnow()
                sent_count += 1
            except Exception as exc:
                logger.warning("send_email_failed", contact=contact.email, error=str(exc))
                sent_email.status = SentEmailStatus.BOUNCED.value
                sent_email.bounce_reason = str(exc)[:255]
                failed_count += 1

            await session.commit()

    logger.info("send_campaign_done", campaign_id=campaign_id, sent=sent_count, failed=failed_count)
    return {"sent": sent_count, "failed": failed_count}
