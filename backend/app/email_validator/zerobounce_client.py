"""ZeroBounce API client — single and batch email verification.

Docs: https://www.zerobounce.net/docs/email-validation-api-quickstart/
Batch endpoint accepts up to 200 emails per request.
"""

from dataclasses import dataclass

import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)

_SINGLE_URL = "https://api.zerobounce.net/v2/validate"
_BATCH_URL = "https://api.zerobounce.net/v2/validatebatch"
_BATCH_SIZE = 200
_TIMEOUT = 30.0

# ZeroBounce status → internal status mapping
_STATUS_MAP: dict[str, str] = {
    "valid": "valid",
    "invalid": "invalid",
    "catch-all": "catch_all",
    "spamtrap": "invalid",
    "abuse": "invalid",
    "do_not_mail": "invalid",
    "unknown": "risky",
}


@dataclass
class ZBResult:
    email: str
    status: str  # valid | invalid | risky | catch_all
    sub_status: str
    score: int  # 0–100 mapped from ZB confidence
    mx_valid: bool
    is_catch_all: bool
    is_disposable: bool
    is_role: bool


def _map_result(item: dict) -> ZBResult:
    zb_status = (item.get("status") or "unknown").lower()
    sub = (item.get("sub_status") or "").lower()
    status = _STATUS_MAP.get(zb_status, "risky")

    is_disposable = sub in ("disposable", "temp_email")
    is_role = sub == "role_based"
    is_catch_all = zb_status == "catch-all"

    if is_disposable:
        status = "disposable"
    elif is_role:
        status = "role_based"

    score_map = {
        "valid": 85,
        "catch_all": 45,
        "risky": 35,
        "invalid": 5,
        "disposable": 5,
        "role_based": 30,
    }
    score = score_map.get(status, 30)

    return ZBResult(
        email=item.get("address", ""),
        status=status,
        sub_status=sub,
        score=score,
        mx_valid=status not in ("invalid", "disposable"),
        is_catch_all=is_catch_all,
        is_disposable=is_disposable,
        is_role=is_role,
    )


class ZeroBounceClient:
    def __init__(self, api_key: str) -> None:
        self._key = api_key

    async def validate(self, email: str) -> ZBResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(_SINGLE_URL, params={"api_key": self._key, "email": email})
            r.raise_for_status()
            return _map_result(r.json())

    async def validate_batch(self, emails: list[str]) -> list[ZBResult]:
        """Validate up to _BATCH_SIZE emails per call; paginates automatically."""
        results: list[ZBResult] = []
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for i in range(0, len(emails), _BATCH_SIZE):
                chunk = emails[i : i + _BATCH_SIZE]
                payload = {
                    "api_key": self._key,
                    "email_batch": [{"email_address": e} for e in chunk],
                }
                r = await client.post(_BATCH_URL, json=payload)
                r.raise_for_status()
                data = r.json()
                for item in data.get("email_batch", []):
                    results.append(_map_result(item))
        return results
