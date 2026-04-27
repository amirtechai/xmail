"""FastAPI dependency injectors."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.core.exceptions import UnauthorizedError
from app.database import get_session
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise UnauthorizedError() from None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError()
    return user


_OPERATOR_ROLES = {UserRole.ADMIN.value, UserRole.OPERATOR.value}


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user


async def require_operator(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role not in _OPERATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
OperatorUser = Annotated[User, Depends(require_operator)]
