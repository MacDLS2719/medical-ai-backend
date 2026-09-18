"""create subscription plans

Revision ID: 04a5246ea95d
Revises: 51c1ca5b3034
Create Date: 2026-09-18 07:12:48.090065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04a5246ea95d'
down_revision: Union[str, Sequence[str], None] = '51c1ca5b3034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
        ),

        sa.Column(
            "slug",
            sa.String(100),
            nullable=False,
            unique=True,
            index=True,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "price",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0.00",
        ),

        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="USD",
        ),

        sa.Column(
            "billing_interval",
            sa.String(20),
            nullable=False,
            server_default="month",
        ),

        sa.Column(
            "is_free",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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


def downgrade() -> None:
    op.drop_table("subscription_plans")