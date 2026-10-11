"""add transcription summary approval

Revision ID: 4ebd2d9c1a70
Revises: 22c496af5312
Create Date: 2026-10-10 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4ebd2d9c1a70"
down_revision: Union[str, Sequence[str], None] = "22c496af5312"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transcription_attachments",
        sa.Column(
            "summary_approved",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "transcription_attachments",
        sa.Column("summary_approved_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_transcription_attachments_summary_approved"),
        "transcription_attachments",
        ["summary_approved"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_transcription_attachments_summary_approved"),
        table_name="transcription_attachments",
    )
    op.drop_column("transcription_attachments", "summary_approved_at")
    op.drop_column("transcription_attachments", "summary_approved")
