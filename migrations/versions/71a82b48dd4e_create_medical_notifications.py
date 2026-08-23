"""create medical notifications

Revision ID: create_medical_notifications
Revises: 66dae21f88c0
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "create_medical_notifications"

down_revision: Union[str, Sequence[str], None] = "66dae21f88c0"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "medical_notifications",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "frequency",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "data",
            sa.JSON(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
    )

    op.create_index(
        "ix_medical_notifications_id",
        "medical_notifications",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_medical_notifications_user_id",
        "medical_notifications",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_medical_notifications_type",
        "medical_notifications",
        ["type"],
        unique=False,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_medical_notifications_type",
        table_name="medical_notifications",
    )

    op.drop_index(
        "ix_medical_notifications_user_id",
        table_name="medical_notifications",
    )

    op.drop_index(
        "ix_medical_notifications_id",
        table_name="medical_notifications",
    )

    op.drop_table(
        "medical_notifications"
    )