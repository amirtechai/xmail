"""Async SMTP client wrapper using aiosmtplib."""

import hashlib
import ssl
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.crypto import get_crypto
from app.core.logger import get_logger
from app.models.smtp_config import SMTPConfiguration
from app.sender.compliance import inject_compliance_footer

logger = get_logger(__name__)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


class SMTPClient:
    def __init__(self, config: SMTPConfiguration) -> None:
        self.config = config
        self._api_key = get_crypto().decrypt(config.password_encrypted)

    async def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        unsubscribe_token: str,
        message_id: str | None = None,
    ) -> str:
        """Send email with compliance footer. Returns message-id."""
        html_final, text_final = inject_compliance_footer(html_body, text_body, unsubscribe_token)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.from_name or ''} <{self.config.from_email}>".strip()
        msg["To"] = to_email
        msg_id = message_id or f"<{uuid.uuid4()}@{self.config.host}>"
        msg["Message-ID"] = msg_id
        msg["List-Unsubscribe"] = f"<{unsubscribe_token}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        msg.attach(MIMEText(text_final, "plain", "utf-8"))
        msg.attach(MIMEText(html_final, "html", "utf-8"))

        context = ssl.create_default_context()
        await aiosmtplib.send(
            msg,
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self._api_key,
            use_tls=self.config.use_tls,
            tls_context=context,
        )
        logger.info("email_sent", to=to_email, message_id=msg_id)
        return msg_id

    @staticmethod
    def body_hash(html_body: str) -> str:
        return _sha256(html_body)
