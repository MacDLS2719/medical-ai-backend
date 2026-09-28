"""create medical search usage

Revision ID: 32409ad0ad06
Revises: e34f8700fc2c
Create Date: 2026-09-27 19:06:38.719186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32409ad0ad06'
down_revision: Union[str, Sequence[str], None] = 'e34f8700fc2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medical_search_usage",

        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "subscription_id",
            sa.BigInteger(),
            nullable=True,
        ),

        sa.Column(
            "search_date",
            sa.Date(),
            nullable=False,
        ),

        sa.Column(
            "search_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
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

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_medical_search_usage_user",
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["doctor_subscriptions.id"],
            name="fk_medical_search_usage_subscription",
            ondelete="SET NULL",
        ),

        sa.UniqueConstraint(
            "user_id",
            "search_date",
            name="uq_medical_search_usage_daily",
        ),
    )

    op.create_index(
        "ix_medical_search_usage_user_date",
        "medical_search_usage",
        ["user_id", "search_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medical_search_usage_user_date",
        table_name="medical_search_usage",
    )

    op.drop_table("medical_search_usage")