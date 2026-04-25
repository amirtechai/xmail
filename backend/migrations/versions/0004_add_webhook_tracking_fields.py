"""Add webhook tracking fields to sent_emails.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sent_emails", sa.Column("recipient_email", sa.String(255), nullable=True))
    op.add_column("sent_emails", sa.Column("bounce_processed", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sent_emails", sa.Column("opened_at", sa.DateTime(), nullable=True))
    op.add_column("sent_emails", sa.Column("clicked_at", sa.DateTime(), nullable=True))
    op.create_index("ix_sent_emails_recipient_email", "sent_emails", ["recipient_email"])


def downgrade() -> None:
    op.drop_index("ix_sent_emails_recipient_email", "sent_emails")
    op.drop_column("sent_emails", "clicked_at")
    op.drop_column("sent_emails", "opened_at")
    op.drop_column("sent_emails", "bounce_processed")
    op.drop_column("sent_emails", "recipient_email")
