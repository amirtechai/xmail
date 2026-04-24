"""Add TOTP 2FA and security columns to users table.

Revision ID: 0001
Revises:
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_encrypted")
