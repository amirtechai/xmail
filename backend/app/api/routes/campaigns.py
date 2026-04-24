"""Campaign CRUD + AI draft + test send + send dispatch + analytics."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.llm.base import LLMMessage
from app.llm.router import build_provider
from app.models.campaign import Campaign, CampaignStatus
from app.models.discovered_contact import DiscoveredContact
from app.models.llm_config import LLMConfiguration
from app.models.sent_email import SentEmail, SentEmailStatus
from app.models.smtp_config import SMTPConfiguration
from app.models.campaign_sequence import CampaignSequence
from app.models.campaign_sequence_step import CampaignSequenceStep
from app.schemas.campaign import (
    AIDraftRequest,
    AIDraftResponse,
    CampaignCreate,
    CampaignOut,
    SendRequest,
    SequenceCreate,
    SequenceStepCreate,
    SequenceStepUpdate,
    SequenceUpdate,
    TestSendRequest,
)
from app.core.security import sanitize_html
from app.sender.compliance import inject_compliance_footer as inject_footer
from app.sender.smtp_client import SMTPClient

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _serialize(c: Campaign) -> dict:
    # Extract extra fields stored in attachments_metadata (our escape hatch for new cols)
    meta = c.attachments_metadata or {}
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "target_audience_keys": c.target_audience_type_ids or [],
        "smtp_config_id": str(c.smtp_config_id) if c.smtp_config_id else None,
        "llm_config_id": str(c.llm_config_id) if c.llm_config_id else None,
        "email_subject": c.email_subject,
        "email_subject_b": meta.get("email_subject_b"),
        "email_body_html": c.email_body_html,
        "email_body_text": c.email_body_text,
        "legitimate_interest_reason": c.legitimate_interest_reason,
        "scheduled_at": meta.get("scheduled_at"),
        "batch_size_per_hour": meta.get("batch_size_per_hour"),
        "dry_run": meta.get("dry_run", False),
        "created_at": c.created_at.isoformat(),
    }


@router.get("/")
async def list_campaigns(session: SessionDep, _: CurrentUser) -> list:
    result = await session.execute(
        select(Campaign).order_by(Campaign.created_at.desc()).limit(100)
    )
    return [_serialize(c) for c in result.scalars().all()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_campaign(body: CampaignCreate, session: SessionDep, user: CurrentUser) -> dict:
    meta = {
        "email_subject_b": body.email_subject_b,
        "scheduled_at": body.scheduled_at.isoformat() if body.scheduled_at else None,
        "batch_size_per_hour": body.batch_size_per_hour,
        "dry_run": body.dry_run,
        "min_confidence": body.min_confidence,
        "target_countries": body.target_countries,
    }
    c = Campaign(
        user_id=user.id,
        name=body.name,
        description=body.description,
        target_audience_type_ids=body.target_audience_keys,
        smtp_config_id=uuid.UUID(body.smtp_config_id) if body.smtp_config_id else None,
        llm_config_id=uuid.UUID(body.llm_config_id) if body.llm_config_id else None,
        email_subject=body.email_subject,
        email_body_html=sanitize_html(body.email_body_html) if body.email_body_html else "",
        email_body_text=body.email_body_text,
        legitimate_interest_reason=body.legitimate_interest_reason,
        attachments_metadata=meta,
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return _serialize(c)


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: uuid.UUID, session: SessionDep, _: CurrentUser) -> dict:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _serialize(c)


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignCreate,
    session: SessionDep,
    user: CurrentUser,
) -> dict:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.status not in (CampaignStatus.DRAFT.value, CampaignStatus.PAUSED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft or paused campaigns can be edited",
        )

    meta = c.attachments_metadata or {}
    meta.update({
        "email_subject_b": body.email_subject_b,
        "scheduled_at": body.scheduled_at.isoformat() if body.scheduled_at else None,
        "batch_size_per_hour": body.batch_size_per_hour,
        "dry_run": body.dry_run,
        "min_confidence": body.min_confidence,
        "target_countries": body.target_countries,
    })
    c.name = body.name
    c.description = body.description
    c.target_audience_type_ids = body.target_audience_keys
    c.smtp_config_id = uuid.UUID(body.smtp_config_id) if body.smtp_config_id else None
    c.llm_config_id = uuid.UUID(body.llm_config_id) if body.llm_config_id else None
    c.email_subject = body.email_subject
    c.email_body_html = sanitize_html(body.email_body_html) if body.email_body_html else ""
    c.email_body_text = body.email_body_text
    c.legitimate_interest_reason = body.legitimate_interest_reason
    c.attachments_metadata = meta
    await session.commit()
    await session.refresh(c)
    return _serialize(c)


@router.post("/{campaign_id}/send", status_code=status.HTTP_202_ACCEPTED)
async def send_campaign(
    campaign_id: uuid.UUID,
    body: SendRequest,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not body.legitimate_interest_reason or len(body.legitimate_interest_reason.strip()) < 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Legitimate interest reason must be at least 20 characters.",
        )

    meta = c.attachments_metadata or {}
    meta["scheduled_at"] = body.scheduled_at.isoformat() if body.scheduled_at else None
    meta["batch_size_per_hour"] = body.batch_size_per_hour
    c.legitimate_interest_reason = body.legitimate_interest_reason
    c.status = CampaignStatus.READY_TO_SEND.value
    c.attachments_metadata = meta
    await session.commit()

    # TODO: enqueue Celery task — campaign_runner.send_campaign.delay(str(campaign_id))
    return {"status": "queued", "campaign_id": str(campaign_id)}


@router.post("/{campaign_id}/test-send")
async def test_send(
    campaign_id: uuid.UUID,
    body: TestSendRequest,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not c.smtp_config_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No SMTP config selected for this campaign.",
        )

    smtp_result = await session.execute(
        select(SMTPConfiguration).where(SMTPConfiguration.id == c.smtp_config_id)
    )
    smtp = smtp_result.scalar_one_or_none()
    if not smtp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SMTP config not found"
        )

    subject = body.subject_override or c.email_subject
    html_with_footer, text_with_footer = inject_footer(
        html_body=c.email_body_html or f"<p>{c.email_body_text}</p>",
        text_body=c.email_body_text or "",
        unsubscribe_token="test-token",
    )
    client = SMTPClient(smtp)
    await client.send_email(
        to=body.to_email,
        subject=f"[TEST] {subject}",
        html=html_with_footer,
        text=text_with_footer,
    )
    return {"status": "sent", "to": body.to_email}


@router.post("/ai-draft", response_model=AIDraftResponse)
async def ai_draft(body: AIDraftRequest, session: SessionDep, _: AdminUser) -> AIDraftResponse:
    # Get LLM config
    if body.llm_config_id:
        llm_result = await session.execute(
            select(LLMConfiguration).where(
                LLMConfiguration.id == uuid.UUID(body.llm_config_id)
            )
        )
    else:
        llm_result = await session.execute(
            select(LLMConfiguration).where(LLMConfiguration.is_active == True).limit(1)  # noqa: E712
        )
    llm_cfg = llm_result.scalar_one_or_none()
    if not llm_cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active LLM configuration found. Add one in Settings → LLM.",
        )

    provider = build_provider(llm_cfg)
    system = (
        "You are an expert B2B email copywriter. Write a concise, professional cold outreach email. "
        "Return a JSON object with keys: subject, body_html, body_text, subject_variants (list of 4 alternative subjects). "
        "The body_html should be clean HTML with paragraph tags. No markdown. No preamble."
    )
    user_msg = (
        f"Audience: {body.audience_key}\n"
        f"Product context: {body.product_context}\n"
        f"Tone: {body.tone}\n"
        f"Language: {body.language}\n"
        "Use personalization variables: {{first_name}}, {{company}}, {{unsubscribe_url}}"
    )

    response = await provider.complete(
        messages=[
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user_msg),
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    import json as _json
    import re

    raw = response.content.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = _json.loads(raw)
        return AIDraftResponse(
            subject=parsed.get("subject", ""),
            body_html=parsed.get("body_html", ""),
            body_text=parsed.get("body_text", ""),
            subject_variants=parsed.get("subject_variants", []),
        )
    except _json.JSONDecodeError:
        # Fallback: return raw as body_text
        return AIDraftResponse(
            subject="",
            body_html=f"<p>{raw}</p>",
            body_text=raw,
            subject_variants=[],
        )


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: uuid.UUID,
    session: SessionDep,
    _: CurrentUser,
) -> dict:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    # Count by status
    status_counts_result = await session.execute(
        select(SentEmail.status, func.count().label("cnt"))
        .where(SentEmail.campaign_id == campaign_id)
        .group_by(SentEmail.status)
    )
    counts: dict[str, int] = {row.status: row.cnt for row in status_counts_result}

    total = sum(counts.values())
    sent = sum(counts.get(s, 0) for s in (
        SentEmailStatus.SENT.value,
        SentEmailStatus.DELIVERED.value,
        SentEmailStatus.OPENED.value,
        SentEmailStatus.CLICKED.value,
        SentEmailStatus.REPLIED.value,
        SentEmailStatus.UNSUBSCRIBED.value,
        SentEmailStatus.BOUNCED.value,
    ))
    delivered = sum(counts.get(s, 0) for s in (
        SentEmailStatus.DELIVERED.value,
        SentEmailStatus.OPENED.value,
        SentEmailStatus.CLICKED.value,
        SentEmailStatus.REPLIED.value,
        SentEmailStatus.UNSUBSCRIBED.value,
    ))
    opened = sum(counts.get(s, 0) for s in (
        SentEmailStatus.OPENED.value,
        SentEmailStatus.CLICKED.value,
        SentEmailStatus.REPLIED.value,
    ))
    clicked = sum(counts.get(s, 0) for s in (
        SentEmailStatus.CLICKED.value,
        SentEmailStatus.REPLIED.value,
    ))
    replied = counts.get(SentEmailStatus.REPLIED.value, 0)
    bounced = counts.get(SentEmailStatus.BOUNCED.value, 0)
    unsubscribed = counts.get(SentEmailStatus.UNSUBSCRIBED.value, 0)

    def rate(n: int, d: int) -> float:
        return round(n / d * 100, 2) if d else 0.0

    bounce_rate = rate(bounced, sent)
    open_rate = rate(opened, delivered)
    click_rate = rate(clicked, opened)
    reply_rate = rate(replied, sent)
    unsub_rate = rate(unsubscribed, sent)

    alerts = []
    if bounce_rate > 2.0:
        alerts.append({"type": "bounce", "message": f"Bounce rate {bounce_rate}% exceeds 2% threshold"})
    if unsub_rate > 0.5:
        alerts.append({"type": "unsub", "message": f"Unsubscribe rate {unsub_rate}% is high"})

    # A/B breakdown
    meta = c.attachments_metadata or {}
    subject_b = meta.get("email_subject_b")
    ab_results = None
    if subject_b:
        ab_a = await session.execute(
            select(func.count()).where(
                SentEmail.campaign_id == campaign_id,
                SentEmail.subject == c.email_subject,
                SentEmail.status.in_([
                    SentEmailStatus.OPENED.value,
                    SentEmailStatus.CLICKED.value,
                    SentEmailStatus.REPLIED.value,
                ]),
            )
        )
        ab_b = await session.execute(
            select(func.count()).where(
                SentEmail.campaign_id == campaign_id,
                SentEmail.subject == subject_b,
                SentEmail.status.in_([
                    SentEmailStatus.OPENED.value,
                    SentEmailStatus.CLICKED.value,
                    SentEmailStatus.REPLIED.value,
                ]),
            )
        )
        ab_a_total = await session.execute(
            select(func.count()).where(
                SentEmail.campaign_id == campaign_id,
                SentEmail.subject == c.email_subject,
            )
        )
        ab_b_total = await session.execute(
            select(func.count()).where(
                SentEmail.campaign_id == campaign_id,
                SentEmail.subject == subject_b,
            )
        )
        ab_results = {
            "subject_a": c.email_subject,
            "subject_b": subject_b,
            "a_sent": ab_a_total.scalar_one(),
            "b_sent": ab_b_total.scalar_one(),
            "a_opened": ab_a.scalar_one(),
            "b_opened": ab_b.scalar_one(),
        }

    return {
        "campaign_id": str(campaign_id),
        "name": c.name,
        "status": c.status,
        "total_queued": total,
        "sent": sent,
        "delivered": delivered,
        "opened": opened,
        "clicked": clicked,
        "replied": replied,
        "bounced": bounced,
        "unsubscribed": unsubscribed,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "bounce_rate": bounce_rate,
        "reply_rate": reply_rate,
        "unsub_rate": unsub_rate,
        "alerts": alerts,
        "ab_results": ab_results,
        "created_at": c.created_at.isoformat(),
    }


# ── Sequences ─────────────────────────────────────────────────────────────────

def _serialize_seq(seq: CampaignSequence, steps: list) -> dict:
    return {
        "id": str(seq.id),
        "campaign_id": str(seq.campaign_id),
        "name": seq.name,
        "is_active": seq.is_active,
        "stop_on_reply": seq.stop_on_reply,
        "created_at": seq.created_at.isoformat(),
        "steps": [
            {
                "id": str(s.id),
                "sequence_id": str(s.sequence_id),
                "step_number": s.step_number,
                "delay_days": s.delay_days,
                "email_subject": s.email_subject,
                "email_body_html": s.email_body_html,
                "email_body_text": s.email_body_text,
                "created_at": s.created_at.isoformat(),
            }
            for s in sorted(steps, key=lambda x: x.step_number)
        ],
    }


@router.get("/{campaign_id}/sequences")
async def list_sequences(
    campaign_id: uuid.UUID,
    session: SessionDep,
    _: CurrentUser,
) -> list:
    seqs = (await session.execute(
        select(CampaignSequence)
        .where(CampaignSequence.campaign_id == campaign_id)
        .order_by(CampaignSequence.created_at)
    )).scalars().all()

    result = []
    for seq in seqs:
        steps = (await session.execute(
            select(CampaignSequenceStep).where(CampaignSequenceStep.sequence_id == seq.id)
        )).scalars().all()
        result.append(_serialize_seq(seq, steps))
    return result


@router.post("/{campaign_id}/sequences", status_code=status.HTTP_201_CREATED)
async def create_sequence(
    campaign_id: uuid.UUID,
    body: SequenceCreate,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    seq = CampaignSequence(
        campaign_id=campaign_id,
        name=body.name,
        is_active=body.is_active,
        stop_on_reply=body.stop_on_reply,
    )
    session.add(seq)
    await session.flush()
    await session.commit()
    await session.refresh(seq)
    return _serialize_seq(seq, [])


@router.patch("/{campaign_id}/sequences/{seq_id}")
async def update_sequence(
    campaign_id: uuid.UUID,
    seq_id: uuid.UUID,
    body: SequenceUpdate,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    seq = (await session.execute(
        select(CampaignSequence).where(
            CampaignSequence.id == seq_id,
            CampaignSequence.campaign_id == campaign_id,
        )
    )).scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    if body.name is not None:
        seq.name = body.name
    if body.is_active is not None:
        seq.is_active = body.is_active
    if body.stop_on_reply is not None:
        seq.stop_on_reply = body.stop_on_reply

    await session.commit()
    await session.refresh(seq)

    steps = (await session.execute(
        select(CampaignSequenceStep).where(CampaignSequenceStep.sequence_id == seq.id)
    )).scalars().all()
    return _serialize_seq(seq, steps)


@router.delete("/{campaign_id}/sequences/{seq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    campaign_id: uuid.UUID,
    seq_id: uuid.UUID,
    session: SessionDep,
    _: AdminUser,
) -> None:
    seq = (await session.execute(
        select(CampaignSequence).where(
            CampaignSequence.id == seq_id,
            CampaignSequence.campaign_id == campaign_id,
        )
    )).scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    await session.execute(
        select(CampaignSequenceStep).where(CampaignSequenceStep.sequence_id == seq_id)
    )
    # Delete steps first, then sequence
    steps = (await session.execute(
        select(CampaignSequenceStep).where(CampaignSequenceStep.sequence_id == seq_id)
    )).scalars().all()
    for s in steps:
        await session.delete(s)
    await session.delete(seq)
    await session.commit()


@router.post("/{campaign_id}/sequences/{seq_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_step(
    campaign_id: uuid.UUID,
    seq_id: uuid.UUID,
    body: SequenceStepCreate,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    seq = (await session.execute(
        select(CampaignSequence).where(
            CampaignSequence.id == seq_id,
            CampaignSequence.campaign_id == campaign_id,
        )
    )).scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    step = CampaignSequenceStep(
        sequence_id=seq_id,
        step_number=body.step_number,
        delay_days=body.delay_days,
        email_subject=body.email_subject,
        email_body_html=body.email_body_html,
        email_body_text=body.email_body_text,
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return {
        "id": str(step.id),
        "sequence_id": str(step.sequence_id),
        "step_number": step.step_number,
        "delay_days": step.delay_days,
        "email_subject": step.email_subject,
        "email_body_html": step.email_body_html,
        "email_body_text": step.email_body_text,
        "created_at": step.created_at.isoformat(),
    }


@router.patch("/{campaign_id}/sequences/{seq_id}/steps/{step_id}")
async def update_step(
    campaign_id: uuid.UUID,
    seq_id: uuid.UUID,
    step_id: uuid.UUID,
    body: SequenceStepUpdate,
    session: SessionDep,
    _: AdminUser,
) -> dict:
    step = (await session.execute(
        select(CampaignSequenceStep).where(
            CampaignSequenceStep.id == step_id,
            CampaignSequenceStep.sequence_id == seq_id,
        )
    )).scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")

    if body.delay_days is not None:
        step.delay_days = body.delay_days
    if body.email_subject is not None:
        step.email_subject = body.email_subject
    if body.email_body_html is not None:
        step.email_body_html = body.email_body_html
    if body.email_body_text is not None:
        step.email_body_text = body.email_body_text

    await session.commit()
    await session.refresh(step)
    return {
        "id": str(step.id),
        "sequence_id": str(step.sequence_id),
        "step_number": step.step_number,
        "delay_days": step.delay_days,
        "email_subject": step.email_subject,
        "email_body_html": step.email_body_html,
        "email_body_text": step.email_body_text,
        "created_at": step.created_at.isoformat(),
    }


@router.delete(
    "/{campaign_id}/sequences/{seq_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_step(
    campaign_id: uuid.UUID,
    seq_id: uuid.UUID,
    step_id: uuid.UUID,
    session: SessionDep,
    _: AdminUser,
) -> None:
    step = (await session.execute(
        select(CampaignSequenceStep).where(
            CampaignSequenceStep.id == step_id,
            CampaignSequenceStep.sequence_id == seq_id,
        )
    )).scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    await session.delete(step)
    await session.commit()


@router.get("/{campaign_id}/recipients")
async def campaign_recipients(
    campaign_id: uuid.UUID,
    session: SessionDep,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
) -> dict:
    q = select(SentEmail).where(SentEmail.campaign_id == campaign_id)
    if status_filter:
        q = q.where(SentEmail.status == status_filter)

    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (
        await session.execute(
            q.order_by(SentEmail.sent_at.desc().nulls_last())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    # Enrich with contact email via contact_id
    contact_emails: dict[str, str] = {}
    contact_ids = [r.contact_id for r in rows if r.contact_id]
    if contact_ids:
        contacts_result = await session.execute(
            select(DiscoveredContact.id, DiscoveredContact.email, DiscoveredContact.full_name)
            .where(DiscoveredContact.id.in_(contact_ids))
        )
        for row in contacts_result:
            contact_emails[str(row.id)] = f"{row.full_name or ''} <{row.email}>"

    items = [
        {
            "id": str(r.id),
            "contact_id": str(r.contact_id) if r.contact_id else None,
            "contact": contact_emails.get(str(r.contact_id), "—") if r.contact_id else "—",
            "subject": r.subject,
            "status": r.status,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "opened_at": r.tracking_pixel_opened_at.isoformat() if r.tracking_pixel_opened_at else None,
            "bounce_reason": r.bounce_reason,
            "click_count": len(r.click_events or []),
        }
        for r in rows
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size}
