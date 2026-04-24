"""Prometheus custom metrics for Xmail."""

from prometheus_client import Counter, Gauge, Histogram

# ── Email sending ────────────────────────────────────────────────────────────

emails_sent_total = Counter(
    "xmail_emails_sent_total",
    "Total emails successfully sent",
    ["campaign_id", "smtp_config"],
)

emails_failed_total = Counter(
    "xmail_emails_failed_total",
    "Total email send failures",
    ["campaign_id", "reason"],
)

email_send_duration_seconds = Histogram(
    "xmail_email_send_duration_seconds",
    "Time taken to send a single email",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ── Campaigns ────────────────────────────────────────────────────────────────

campaigns_by_status = Gauge(
    "xmail_campaigns_by_status",
    "Number of campaigns grouped by status",
    ["status"],
)

# ── Contacts ─────────────────────────────────────────────────────────────────

contacts_discovered_total = Counter(
    "xmail_contacts_discovered_total",
    "Total contacts discovered by the bot",
)

contacts_suppressed_total = Counter(
    "xmail_contacts_suppressed_total",
    "Total contacts added to suppression list",
    ["reason"],
)

# ── Bot / Agent ──────────────────────────────────────────────────────────────

bot_runs_total = Counter(
    "xmail_bot_runs_total",
    "Total agent run cycles",
    ["run_type", "result"],
)

bot_run_duration_seconds = Histogram(
    "xmail_bot_run_duration_seconds",
    "Duration of full agent run cycles",
    buckets=[5, 15, 30, 60, 120, 300, 600],
)

celery_queue_depth = Gauge(
    "xmail_celery_queue_depth",
    "Current number of tasks in Celery queue",
    ["queue"],
)

# ── Auth / Security ──────────────────────────────────────────────────────────

login_attempts_total = Counter(
    "xmail_login_attempts_total",
    "Total login attempts",
    ["result"],  # success | failure | locked
)

totp_verifications_total = Counter(
    "xmail_totp_verifications_total",
    "Total TOTP verification attempts",
    ["result"],  # success | failure
)
