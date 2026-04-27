"""Add replied_at to sent_emails for IMAP reply detection.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sent_emails", sa.Column("replied_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("sent_emails", "replied_at")
