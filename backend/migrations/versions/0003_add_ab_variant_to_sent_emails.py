"""Add ab_variant column to sent_emails.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sent_emails", sa.Column("ab_variant", sa.String(length=1), nullable=True))


def downgrade() -> None:
    op.drop_column("sent_emails", "ab_variant")
