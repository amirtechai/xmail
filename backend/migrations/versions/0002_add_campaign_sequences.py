"""Add campaign_sequences, campaign_sequence_steps tables and sequence_step_id to sent_emails.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="Follow-up sequence"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("stop_on_reply", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_sequences_campaign_id", "campaign_sequences", ["campaign_id"])

    op.create_table(
        "campaign_sequence_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("email_subject", sa.String(255), nullable=False, server_default=""),
        sa.Column("email_body_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("email_body_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seq_step_sequence_number", "campaign_sequence_steps", ["sequence_id", "step_number"])
    op.create_index("ix_campaign_sequence_steps_sequence_id", "campaign_sequence_steps", ["sequence_id"])

    op.add_column("sent_emails", sa.Column("sequence_step_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_sent_emails_sequence_step_id", "sent_emails", ["sequence_step_id"])


def downgrade() -> None:
    op.drop_index("ix_sent_emails_sequence_step_id", table_name="sent_emails")
    op.drop_column("sent_emails", "sequence_step_id")
    op.drop_index("ix_campaign_sequence_steps_sequence_id", table_name="campaign_sequence_steps")
    op.drop_index("ix_seq_step_sequence_number", table_name="campaign_sequence_steps")
    op.drop_table("campaign_sequence_steps")
    op.drop_index("ix_campaign_sequences_campaign_id", table_name="campaign_sequences")
    op.drop_table("campaign_sequences")
