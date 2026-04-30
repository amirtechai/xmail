"""LLM configuration CRUD + test endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, SessionDep
from app.core.crypto import get_crypto
from app.llm.base import LLMMessage
from app.llm.router import build_provider
from app.models.llm_config import LLMConfiguration
from app.schemas.llm import LLMConfigCreate, LLMConfigOut, LLMTestRequest, LLMTestResponse

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/", response_model=list[LLMConfigOut])
async def list_configs(session: SessionDep, _: AdminUser) -> list[LLMConfiguration]:
    result = await session.execute(select(LLMConfiguration))
    return list(result.scalars().all())


@router.post("/", response_model=LLMConfigOut, status_code=status.HTTP_201_CREATED)
async def create_config(
    body: LLMConfigCreate, session: SessionDep, admin_user: AdminUser
) -> LLMConfiguration:
    crypto = get_crypto()
    if body.is_default:
        existing = (await session.execute(select(LLMConfiguration))).scalars().all()
        for c in existing:
            c.is_default = False
    config = LLMConfiguration(
        user_id=admin_user.id,
        provider=body.provider,
        selected_model=body.model_name,
        api_key_encrypted=crypto.encrypt(body.api_key),
        base_url=body.base_url,
        is_default=body.is_default,
        purpose=body.purpose,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(config_id: uuid.UUID, session: SessionDep, _: AdminUser) -> None:
    result = await session.execute(select(LLMConfiguration).where(LLMConfiguration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found")
    await session.delete(config)
    await session.commit()


@router.post("/{config_id}/set-default", response_model=LLMConfigOut)
async def set_default(config_id: uuid.UUID, session: SessionDep, _: AdminUser) -> LLMConfiguration:
    all_configs = (await session.execute(select(LLMConfiguration))).scalars().all()
    target = next((c for c in all_configs if c.id == config_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found")
    for c in all_configs:
        c.is_default = c.id == config_id
    await session.commit()
    await session.refresh(target)
    return target


@router.post("/{config_id}/test", response_model=LLMTestResponse)
async def test_config(
    config_id: uuid.UUID,
    body: LLMTestRequest,
    session: SessionDep,
    _: AdminUser,
) -> LLMTestResponse:
    result = await session.execute(select(LLMConfiguration).where(LLMConfiguration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found")
    try:
        provider = build_provider(config)
        response = await provider.complete([LLMMessage(role="user", content=body.prompt)])
        return LLMTestResponse(
            success=True,
            content=response.content,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
    except Exception as exc:
        return LLMTestResponse(success=False, error=str(exc))
