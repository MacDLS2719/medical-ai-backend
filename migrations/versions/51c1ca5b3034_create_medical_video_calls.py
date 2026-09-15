"""create medical video calls

Revision ID: 51c1ca5b3034
Revises: 8353eabaa011
Create Date: 2026-09-15 12:25:16.771441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51c1ca5b3034'
down_revision: Union[str, Sequence[str], None] = '8353eabaa011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medical_video_calls",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey(
                "medical_conversations.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "caller_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "receiver_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "room_name",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "room_url",
            sa.String(1000),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="calling",
        ),

        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "ended_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "duration",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_medical_video_calls_conversation_id",
        "medical_video_calls",
        ["conversation_id"],
        unique=False,
    )

    op.create_index(
        "ix_medical_video_calls_caller_id",
        "medical_video_calls",
        ["caller_id"],
        unique=False,
    )

    op.create_index(
        "ix_medical_video_calls_receiver_id",
        "medical_video_calls",
        ["receiver_id"],
        unique=False,
    )

    op.create_index(
        "ix_medical_video_calls_status",
        "medical_video_calls",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medical_video_calls_status",
        table_name="medical_video_calls",
    )

    op.drop_index(
        "ix_medical_video_calls_receiver_id",
        table_name="medical_video_calls",
    )

    op.drop_index(
        "ix_medical_video_calls_caller_id",
        table_name="medical_video_calls",
    )

    op.drop_index(
        "ix_medical_video_calls_conversation_id",
        table_name="medical_video_calls",
    )

    op.drop_table("medical_video_calls")