"""4-stage email validation orchestrator."""

from dataclasses import dataclass

from app.email_validator.dea_check import is_disposable
from app.email_validator.mx_check import has_mx_record
from app.email_validator.role_check import is_role_address
from app.email_validator.smtp_check import check_smtp
from app.email_validator.syntax import is_valid_syntax


@dataclass
class ValidationResult:
    email: str
    status: str          # valid | invalid | risky | catch_all | disposable | role_based
    score: int           # 0–100
    mx_valid: bool
    is_catch_all: bool
    is_disposable: bool
    is_role: bool


async def validate_email(email: str, redis_client=None) -> ValidationResult:  # type: ignore[no-untyped-def]
    email = email.strip().lower()

    # Stage 1: Syntax
    if not is_valid_syntax(email):
        return ValidationResult(email=email, status="invalid", score=0,
                                mx_valid=False, is_catch_all=False,
                                is_disposable=False, is_role=False)

    domain = email.split("@")[1]
    is_disp = is_disposable(email)
    is_role = is_role_address(email)

    if is_disp:
        return ValidationResult(email=email, status="disposable", score=5,
                                mx_valid=False, is_catch_all=False,
                                is_disposable=True, is_role=is_role)

    # Stage 2: MX
    mx_ok = await has_mx_record(domain, redis_client)
    if not mx_ok:
        return ValidationResult(email=email, status="invalid", score=10,
                                mx_valid=False, is_catch_all=False,
                                is_disposable=False, is_role=is_role)

    # Stage 3: SMTP probe
    try:
        exists, catch_all = await check_smtp(email)
    except Exception:
        exists, catch_all = False, False

    if is_role:
        status = "role_based"
        score = 30
    elif catch_all:
        status = "catch_all"
        score = 45
    elif exists:
        status = "valid"
        score = 85
    else:
        status = "risky"
        score = 40

    return ValidationResult(
        email=email,
        status=status,
        score=score,
        mx_valid=mx_ok,
        is_catch_all=catch_all,
        is_disposable=False,
        is_role=is_role,
    )
