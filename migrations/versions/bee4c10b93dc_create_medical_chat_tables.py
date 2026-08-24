"""create medical chat tables

Revision ID: b7c4e91a2f63
Revises: 825129e40dd8
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c4e91a2f63"
down_revision: Union[str, Sequence[str], None] = "825129e40dd8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================
    # MEDICAL CONVERSATIONS
    # ==========================================================

    op.create_table(
        "medical_conversations",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False
        ),

        sa.Column(
            "patient_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "doctor_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active"
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["users.id"],
            ondelete="CASCADE"
        )
    )

    op.create_index(
        "ix_medical_conversations_patient_id",
        "medical_conversations",
        ["patient_id"]
    )

    op.create_index(
        "ix_medical_conversations_doctor_id",
        "medical_conversations",
        ["doctor_id"]
    )

    # ==========================================================
    # MEDICAL MESSAGES
    # ==========================================================

    op.create_table(
        "medical_messages",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False
        ),

        sa.Column(
            "conversation_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "sender_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "receiver_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "message",
            sa.Text(),
            nullable=False
        ),

        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        ),

        sa.Column(
            "read_at",
            sa.DateTime(),
            nullable=True
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["medical_conversations.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["users.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["receiver_id"],
            ["users.id"],
            ondelete="CASCADE"
        )
    )

    op.create_index(
        "ix_medical_messages_conversation_id",
        "medical_messages",
        ["conversation_id"]
    )

    op.create_index(
        "ix_medical_messages_sender_id",
        "medical_messages",
        ["sender_id"]
    )

    op.create_index(
        "ix_medical_messages_receiver_id",
        "medical_messages",
        ["receiver_id"]
    )

    # ==========================================================
    # MEDICAL MESSAGES NOTIFICATIONS
    # ==========================================================

    op.create_table(
        "medical_messages_notifications",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False
        ),

        sa.Column(
            "message_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
            server_default="new_message"
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False
        ),

        sa.Column(
            "message",
            sa.Text(),
            nullable=False
        ),

        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.ForeignKeyConstraint(
            ["message_id"],
            ["medical_messages.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE"
        )
    )

    op.create_index(
        "ix_medical_messages_notifications_message_id",
        "medical_messages_notifications",
        ["message_id"]
    )

    op.create_index(
        "ix_medical_messages_notifications_user_id",
        "medical_messages_notifications",
        ["user_id"]
    )


def downgrade() -> None:

    # ==========================================================
    # MEDICAL MESSAGE NOTIFICATIONS
    # ==========================================================

    op.drop_index(
        "ix_medical_messages_notifications_user_id",
        table_name="medical_messages_notifications"
    )

    op.drop_index(
        "ix_medical_messages_notifications_message_id",
        table_name="medical_messages_notifications"
    )

    op.drop_table(
        "medical_messages_notifications"
    )

    # ==========================================================
    # MEDICAL MESSAGES
    # ==========================================================

    op.drop_index(
        "ix_medical_messages_receiver_id",
        table_name="medical_messages"
    )

    op.drop_index(
        "ix_medical_messages_sender_id",
        table_name="medical_messages"
    )

    op.drop_index(
        "ix_medical_messages_conversation_id",
        table_name="medical_messages"
    )

    op.drop_table(
        "medical_messages"
    )

    # ==========================================================
    # MEDICAL CONVERSATIONS
    # ==========================================================

    op.drop_index(
        "ix_medical_conversations_doctor_id",
        table_name="medical_conversations"
    )

    op.drop_index(
        "ix_medical_conversations_patient_id",
        table_name="medical_conversations"
    )

    op.drop_table(
        "medical_conversations"
    )