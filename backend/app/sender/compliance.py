"""GDPR/CAN-SPAM/CASL compliance footer injection."""

from app.config import settings

_HTML_FOOTER_TEMPLATE = """
<br><br>
<table width="100%" cellpadding="0" cellspacing="0" role="presentation">
  <tr>
    <td style="font-size:11px;color:#888888;text-align:center;padding:10px 0;">
      <p>{company_address}</p>
      <p>
        You received this email because of your public professional profile.<br>
        <a href="{unsubscribe_url}" style="color:#888888;">Unsubscribe</a> &nbsp;|&nbsp;
        <a href="{unsubscribe_url}?reason=legal" style="color:#888888;">Legal Basis</a>
      </p>
    </td>
  </tr>
</table>
{pixel}
"""

_TEXT_FOOTER_TEMPLATE = """

---
{company_address}

You received this email because of your public professional profile.
To unsubscribe: {unsubscribe_url}
"""


def build_unsubscribe_url(token: str) -> str:
    return f"{settings.unsubscribe_base_url}/{token}"


def inject_compliance_footer(
    html_body: str,
    text_body: str,
    unsubscribe_token: str,
    sent_email_id: str | None = None,
) -> tuple[str, str]:
    url = build_unsubscribe_url(unsubscribe_token)
    pixel = (
        f'<img src="{settings.tracking_base_url}/o/{sent_email_id}.gif"'
        ' width="1" height="1" alt="" style="display:none;" />'
        if sent_email_id else ""
    )
    footer_html = _HTML_FOOTER_TEMPLATE.format(
        company_address=settings.company_physical_address,
        unsubscribe_url=url,
        pixel=pixel,
    )
    footer_text = _TEXT_FOOTER_TEMPLATE.format(
        company_address=settings.company_physical_address,
        unsubscribe_url=url,
    )
    return html_body + footer_html, text_body + footer_text


def check_suppression_required(bounce_count: int, complaint: bool) -> bool:
    """Returns True if contact must be added to suppression list."""
    return complaint or bounce_count >= 2
