"""create daily_transcriptions table

Revision ID: e29f45e42041
Revises: 6fca01e9b941
Create Date: 2026-10-10 10:10:20.797241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e29f45e42041"
down_revision: Union[str, Sequence[str], None] = "6fca01e9b941"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_transcriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_name", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("doctor_id", sa.Integer(), nullable=True),
        sa.Column("patient_name", sa.String(length=255), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("download_url", sa.String(length=2000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("doctor_id", "id", "room_name", "session_id", "status"):
        op.create_index(
            op.f(f"ix_daily_transcriptions_{column}"),
            "daily_transcriptions",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("status", "session_id", "room_name", "id", "doctor_id"):
        op.drop_index(
            op.f(f"ix_daily_transcriptions_{column}"),
            table_name="daily_transcriptions",
        )
    op.drop_table("daily_transcriptions")
