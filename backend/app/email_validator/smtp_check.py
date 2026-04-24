"""SMTP RCPT-TO check for mailbox existence and catch-all detection."""

import asyncio
import socket

import dns.asyncresolver
import dns.exception

from app.core.logger import get_logger

logger = get_logger(__name__)
_SMTP_TIMEOUT = 10


async def _get_mx_host(domain: str) -> str | None:
    try:
        answers = await dns.asyncresolver.resolve(domain, "MX")
        best = sorted(answers, key=lambda r: r.preference)[0]
        return str(best.exchange).rstrip(".")
    except Exception:
        return None


async def check_smtp(email: str) -> tuple[bool, bool]:
    """
    Returns (mailbox_exists, is_catch_all).
    Uses HELO → MAIL FROM → RCPT TO without sending.
    Also probes a random address to detect catch-all.
    """
    domain = email.split("@")[-1]
    mx = await _get_mx_host(domain)
    if not mx:
        return False, False

    async def _probe(address: str) -> bool:
        try:
            loop = asyncio.get_event_loop()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(mx, 25),
                timeout=_SMTP_TIMEOUT,
            )
            async def recv() -> str:
                return (await reader.read(512)).decode(errors="ignore")

            await recv()  # 220 banner
            writer.write(b"HELO xmail.check\r\n")
            await writer.drain()
            await recv()
            writer.write(b"MAIL FROM:<check@xmail.check>\r\n")
            await writer.drain()
            await recv()
            writer.write(f"RCPT TO:<{address}>\r\n".encode())
            await writer.drain()
            response = await recv()
            writer.write(b"QUIT\r\n")
            await writer.drain()
            writer.close()
            return response.startswith("250")
        except Exception:
            return False

    exists = await _probe(email)
    # Probe random address to detect catch-all
    random_addr = f"xmail_noreply_9z7x@{domain}"
    catch_all_hit = await _probe(random_addr)
    return exists, catch_all_hit
