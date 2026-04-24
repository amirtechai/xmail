"""Authentication endpoints with brute-force protection and TOTP 2FA."""

import base64
import io

import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, Request, status
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.crypto import get_crypto
from app.core.exceptions import UnauthorizedError
from app.core.metrics import login_attempts_total, totp_verifications_total
from app.models.user import User
from app.schemas.user import LoginRequest, RefreshRequest, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Rate limit helper (Redis) ─────────────────────────────────────────────────


async def _get_redis():  # type: ignore[return]
    from app.database import get_redis
    return await get_redis()


# ── Login ─────────────────────────────────────────────────────────────────────


class LoginResponse(BaseModel):
    """Either full tokens (no 2FA) or a short-lived TOTP challenge token."""
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    requires_totp: bool = False
    totp_token: str | None = None  # short-lived challenge token (2 min)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, session: SessionDep) -> LoginResponse:
    from app.core.security import (
        clear_failed_attempts,
        is_account_locked,
        record_failed_attempt,
    )

    try:
        redis = await _get_redis()
        locked = await is_account_locked(redis, body.email)
        if locked:
            login_attempts_total.labels(result="locked").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked. Try again in 15 minutes.",
            )
    except HTTPException:
        raise
    except Exception:
        redis = None

    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        if redis:
            await record_failed_attempt(redis, body.email)
        login_attempts_total.labels(result="failure").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Successful credential check — clear brute-force counter
    if redis:
        await clear_failed_attempts(redis, body.email)
    login_attempts_total.labels(result="success").inc()

    # Update last login
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    await session.commit()

    # If TOTP enabled, issue a short-lived challenge token instead of full tokens
    if user.totp_enabled:
        challenge = create_access_token(str(user.id), expires_delta=__import__("datetime").timedelta(minutes=2))
        return LoginResponse(requires_totp=True, totp_token=challenge)

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ── TOTP verify-login (second factor) ────────────────────────────────────────


class TOTPLoginRequest(BaseModel):
    totp_token: str
    code: str


@router.post("/totp/verify-login", response_model=TokenPair)
async def verify_totp_login(body: TOTPLoginRequest, session: SessionDep) -> TokenPair:
    try:
        payload = decode_token(body.totp_token)
        if payload.get("type") != "access":
            raise UnauthorizedError()
        user_id: str = payload["sub"]
    except JWTError:
        raise UnauthorizedError("Invalid challenge token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.totp_enabled or not user.totp_secret_encrypted:
        raise UnauthorizedError()

    secret = get_crypto().decrypt(user.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        totp_verifications_total.labels(result="failure").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")

    totp_verifications_total.labels(result="success").inc()
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ── TOTP setup ────────────────────────────────────────────────────────────────


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_data_url: str  # base64 PNG for frontend QR display


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(current_user: CurrentUser, session: SessionDep) -> TOTPSetupResponse:
    if current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP already enabled")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="Xmail")

    # Generate QR code PNG → data URL
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    qr_data_url = f"data:image/png;base64,{qr_b64}"

    # Store the unencrypted secret temporarily in session (not saved until confirmed)
    # Return to client; they confirm with a code before we persist
    return TOTPSetupResponse(secret=secret, provisioning_uri=uri, qr_data_url=qr_data_url)


class TOTPConfirmRequest(BaseModel):
    secret: str
    code: str


@router.post("/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_totp(body: TOTPConfirmRequest, current_user: CurrentUser, session: SessionDep) -> None:
    """Verify the code matches the secret, then persist encrypted secret and enable TOTP."""
    totp = pyotp.TOTP(body.secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    user.totp_secret_encrypted = get_crypto().encrypt(body.secret)
    user.totp_enabled = True
    await session.commit()


@router.post("/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_totp(body: TOTPConfirmRequest, current_user: CurrentUser, session: SessionDep) -> None:
    """Require a valid TOTP code to disable 2FA."""
    if not current_user.totp_enabled or not current_user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not enabled")
    secret = get_crypto().decrypt(current_user.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")

    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    user.totp_secret_encrypted = None
    user.totp_enabled = False
    await session.commit()


# ── Password change ───────────────────────────────────────────────────────────


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: PasswordChangeRequest, current_user: CurrentUser, session: SessionDep) -> None:
    if len(body.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password incorrect")
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    user.password_hash = hash_password(body.new_password)
    await session.commit()


# ── Refresh + me ──────────────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise UnauthorizedError()

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError()

    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> User:
    return current_user
