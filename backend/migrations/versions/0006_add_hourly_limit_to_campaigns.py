"""Add hourly_limit to campaigns.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("hourly_limit", sa.Integer(), nullable=False, server_default="50"),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "hourly_limit")
