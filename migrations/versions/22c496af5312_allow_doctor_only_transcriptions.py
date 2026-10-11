"""allow doctor-only transcription records

Revision ID: 22c496af5312
Revises: c4160e2f8a1b
Create Date: 2026-10-10 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "22c496af5312"
down_revision: Union[str, Sequence[str], None] = "c4160e2f8a1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "transcription_attachments",
        "conversation_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "transcription_attachments",
        "patient_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "transcription_attachments",
        "patient_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "transcription_attachments",
        "conversation_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
