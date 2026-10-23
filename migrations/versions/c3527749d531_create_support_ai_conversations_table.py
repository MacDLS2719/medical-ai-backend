"""create support ai conversations table

Revision ID: c3527749d531
Revises: d3e24f02d253
Create Date: 2026-10-21 18:41:38.237946

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3527749d531'
down_revision: Union[str, Sequence[str], None] = 'd3e24f02d253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_ai_conversations",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=False,
        ),
        sa.Column(
            "question",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "answer",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_support_ai_conversations_user_id",
        "support_ai_conversations",
        ["user_id"],
    )

    op.create_index(
        "ix_support_ai_conversations_conversation_id",
        "support_ai_conversations",
        ["conversation_id"],
    )

    op.create_index(
        "ix_support_ai_conversations_created_at",
        "support_ai_conversations",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_support_ai_conversations_created_at",
        table_name="support_ai_conversations",
    )
    op.drop_index(
        "ix_support_ai_conversations_conversation_id",
        table_name="support_ai_conversations",
    )
    op.drop_index(
        "ix_support_ai_conversations_user_id",
        table_name="support_ai_conversations",
    )
    op.drop_table("support_ai_conversations")
