"""create transcription attachments table

Revision ID: c4160e2f8a1b
Revises: 0587e6432416, 6fca01e9b941, a61481083f3e, create_medical_notifications, e29f45e42041
Create Date: 2026-10-10 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4160e2f8a1b"
down_revision: Union[str, Sequence[str], None] = (
    "0587e6432416",
    "6fca01e9b941",
    "a61481083f3e",
    "create_medical_notifications",
    "e29f45e42041",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transcription_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("recording_url", sa.String(length=2000), nullable=False),
        sa.Column("recording_public_id", sa.String(length=500), nullable=True),
        sa.Column("recording_file_name", sa.String(length=255), nullable=False),
        sa.Column("recording_mime_type", sa.String(length=100), nullable=False),
        sa.Column("recording_file_size", sa.BigInteger(), nullable=True),
        sa.Column("transcript_file_url", sa.String(length=2000), nullable=True),
        sa.Column("transcript_file_public_id", sa.String(length=500), nullable=True),
        sa.Column("transcript_file_name", sa.String(length=255), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="processing",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["medical_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transcription_attachments_id"),
        "transcription_attachments",
        ["id"],
        unique=False,
    )
    for column in ("conversation_id", "patient_id", "doctor_id", "status", "recorded_at"):
        op.create_index(
            op.f(f"ix_transcription_attachments_{column}"),
            "transcription_attachments",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("recorded_at", "status", "doctor_id", "patient_id", "conversation_id", "id"):
        op.drop_index(
            op.f(f"ix_transcription_attachments_{column}"),
            table_name="transcription_attachments",
        )
    op.drop_table("transcription_attachments")
