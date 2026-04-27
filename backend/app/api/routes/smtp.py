"""SMTP configuration CRUD + test endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, SessionDep
from app.core.crypto import get_crypto
from app.models.smtp_config import SMTPConfiguration
from app.schemas.smtp import SMTPConfigCreate, SMTPConfigOut, SMTPTestRequest, SMTPTestResponse
from app.sender.smtp_client import SMTPClient

router = APIRouter(prefix="/smtp", tags=["smtp"])


@router.get("/", response_model=list[SMTPConfigOut])
async def list_configs(session: SessionDep, _: AdminUser) -> list[SMTPConfiguration]:
    result = await session.execute(select(SMTPConfiguration))
    return list(result.scalars().all())


@router.post("/", response_model=SMTPConfigOut, status_code=status.HTTP_201_CREATED)
async def create_config(
    body: SMTPConfigCreate, session: SessionDep, _: AdminUser
) -> SMTPConfiguration:
    crypto = get_crypto()
    if body.is_default:
        # clear existing default
        existing = (await session.execute(select(SMTPConfiguration))).scalars().all()
        for c in existing:
            c.is_default = False
    config = SMTPConfiguration(
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        password_encrypted=crypto.encrypt(body.password),
        use_tls=body.use_tls,
        from_email=body.from_email,
        from_name=body.from_name,
        daily_send_limit=body.daily_send_limit,
        is_default=body.is_default,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(config_id: uuid.UUID, session: SessionDep, _: AdminUser) -> None:
    result = await session.execute(
        select(SMTPConfiguration).where(SMTPConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP config not found")
    await session.delete(config)
    await session.commit()


@router.post("/{config_id}/set-default", response_model=SMTPConfigOut)
async def set_default(config_id: uuid.UUID, session: SessionDep, _: AdminUser) -> SMTPConfiguration:
    all_configs = (await session.execute(select(SMTPConfiguration))).scalars().all()
    target = next((c for c in all_configs if c.id == config_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP config not found")
    for c in all_configs:
        c.is_default = c.id == config_id
    await session.commit()
    await session.refresh(target)
    return target


@router.post("/{config_id}/test", response_model=SMTPTestResponse)
async def test_smtp(
    config_id: uuid.UUID,
    body: SMTPTestRequest,
    session: SessionDep,
    _: AdminUser,
) -> SMTPTestResponse:
    result = await session.execute(
        select(SMTPConfiguration).where(SMTPConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP config not found")
    try:
        client = SMTPClient(config)
        await client.send(
            to_email=body.to_email,
            subject=body.subject,
            html_body="<p>This is a test email from Xmail.</p>",
            text_body="This is a test email from Xmail.",
            unsubscribe_token="test-token",
        )
        return SMTPTestResponse(success=True)
    except Exception as exc:
        return SMTPTestResponse(success=False, error=str(exc))
