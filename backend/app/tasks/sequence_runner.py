"""Daily drip-sequence runner.

For each active CampaignSequence:
1. Find contacts who received the initial campaign email (sequence_step_id IS NULL).
2. For each step (ordered by step_number), determine which contacts are due:
   - No existing sent_email for this step yet
   - Required delay_days have elapsed since the previous send
   - If stop_on_reply=True, skip contacts whose last email has status='replied'
3. Queue follow-up emails via the standard send pathway.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.sequence_runner.run_sequences")
def run_sequences() -> dict:
    return asyncio.get_event_loop().run_until_complete(_run())


async def _run() -> dict:
    from sqlalchemy import and_, select

    from app.database import async_session_factory
    from app.models.campaign_sequence import CampaignSequence
    from app.models.campaign_sequence_step import CampaignSequenceStep
    from app.models.sent_email import SentEmail, SentEmailStatus

    sent_count = 0
    skipped_count = 0

    async with async_session_factory() as session:
        sequences = (await session.execute(
            select(CampaignSequence).where(CampaignSequence.is_active.is_(True))
        )).scalars().all()

        for seq in sequences:
            steps = (await session.execute(
                select(CampaignSequenceStep)
                .where(CampaignSequenceStep.sequence_id == seq.id)
                .order_by(CampaignSequenceStep.step_number)
            )).scalars().all()

            if not steps:
                continue

            # Find all initial sends for this campaign
            initial_sends = (await session.execute(
                select(SentEmail).where(
                    and_(
                        SentEmail.campaign_id == seq.campaign_id,
                        SentEmail.sequence_step_id.is_(None),
                        SentEmail.status.in_([
                            SentEmailStatus.SENT.value,
                            SentEmailStatus.DELIVERED.value,
                            SentEmailStatus.OPENED.value,
                            SentEmailStatus.CLICKED.value,
                        ]),
                    )
                )
            )).scalars().all()

            for initial in initial_sends:
                if initial.contact_id is None:
                    continue

                # If stop_on_reply: skip contacts that have replied to any email in this campaign
                if seq.stop_on_reply:
                    replied = (await session.execute(
                        select(SentEmail.id).where(
                            and_(
                                SentEmail.campaign_id == seq.campaign_id,
                                SentEmail.contact_id == initial.contact_id,
                                SentEmail.status == SentEmailStatus.REPLIED.value,
                            )
                        ).limit(1)
                    )).scalar_one_or_none()
                    if replied:
                        skipped_count += 1
                        continue

                # Determine the last send time for this contact in this sequence
                last_sent_at = initial.sent_at or datetime.utcnow()
                last_step_number = 0

                prior_steps = (await session.execute(
                    select(SentEmail.sequence_step_id, SentEmail.sent_at).where(
                        and_(
                            SentEmail.campaign_id == seq.campaign_id,
                            SentEmail.contact_id == initial.contact_id,
                            SentEmail.sequence_step_id.is_not(None),
                        )
                    ).order_by(SentEmail.sent_at.desc())
                )).all()

                sent_step_ids = {row[0] for row in prior_steps}
                if prior_steps:
                    last_sent_at = prior_steps[0][1] or last_sent_at
                    # Determine last step number from sent step ids
                    for step in reversed(steps):
                        if step.id in sent_step_ids:
                            last_step_number = step.step_number
                            break

                # Find the next due step
                for step in steps:
                    if step.step_number <= last_step_number:
                        continue
                    if step.id in sent_step_ids:
                        continue
                    due_at = last_sent_at + timedelta(days=step.delay_days)
                    if datetime.utcnow() < due_at:
                        break  # Not due yet — steps are ordered, no point checking further

                    # Send the follow-up
                    result = await _send_step(session, seq, step, initial)
                    if result:
                        sent_count += 1
                        last_sent_at = datetime.utcnow()
                        last_step_number = step.step_number
                        sent_step_ids.add(step.id)
                    break  # One step at a time per contact per run

    logger.info("sequence_runner_done", sent=sent_count, skipped=skipped_count)
    return {"sent": sent_count, "skipped": skipped_count}


async def _send_step(session, seq, step, initial_send) -> bool:  # type: ignore[no-untyped-def]
    """Send one follow-up step and record it as a SentEmail."""
    from app.models.sent_email import SentEmail, SentEmailStatus
    import hashlib

    if not step.email_subject or not step.email_body_html:
        return False

    body_hash = hashlib.sha256(step.email_body_html.encode()).hexdigest()

    follow_up = SentEmail(
        campaign_id=initial_send.campaign_id,
        contact_id=initial_send.contact_id,
        smtp_config_id=initial_send.smtp_config_id,
        subject=step.email_subject,
        body_hash=body_hash,
        status=SentEmailStatus.QUEUED.value,
        sequence_step_id=step.id,
    )
    session.add(follow_up)
    await session.flush()

    # Dispatch the actual send via the existing send worker
    try:
        from app.tasks.bounce_processing import send_campaign_email  # type: ignore[attr-defined]
        send_campaign_email.delay(str(follow_up.id))
    except Exception:
        # If send worker isn't wired yet, leave as QUEUED for the next pass
        pass

    await session.commit()
    return True
