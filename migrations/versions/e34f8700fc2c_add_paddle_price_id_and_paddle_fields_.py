"""add_paddle_price_id_and_paddle_fields_to_payments

Revision ID: e34f8700fc2c
Revises: d0909cc9cda5
Create Date: 2026-09-21 21:52:51.841845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e34f8700fc2c'
down_revision: Union[str, Sequence[str], None] = 'd0909cc9cda5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega:
      1. subscription_plans.paddle_price_id  — mapeo con Paddle Price ID
      2. payments_doctor.paddle_transaction_id
      3. payments_doctor.paddle_subscription_id
    """

    # ------------------------------------------------------------------
    # 1. subscription_plans.paddle_price_id
    # ------------------------------------------------------------------
    op.add_column(
        'subscription_plans',
        sa.Column(
            'paddle_price_id',
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_subscription_plans_paddle_price_id',
        'subscription_plans',
        ['paddle_price_id'],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 2. payments_doctor.paddle_transaction_id
    # ------------------------------------------------------------------
    op.add_column(
        'payments_doctor',
        sa.Column(
            'paddle_transaction_id',
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_payments_doctor_paddle_transaction_id',
        'payments_doctor',
        ['paddle_transaction_id'],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 3. payments_doctor.paddle_subscription_id
    # ------------------------------------------------------------------
    op.add_column(
        'payments_doctor',
        sa.Column(
            'paddle_subscription_id',
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_payments_doctor_paddle_subscription_id',
        'payments_doctor',
        ['paddle_subscription_id'],
        unique=False,
    )


def downgrade() -> None:
    """
    Revierte las columnas añadidas en upgrade().
    """

    op.drop_index(
        'ix_payments_doctor_paddle_subscription_id',
        table_name='payments_doctor',
    )
    op.drop_column('payments_doctor', 'paddle_subscription_id')

    op.drop_index(
        'ix_payments_doctor_paddle_transaction_id',
        table_name='payments_doctor',
    )
    op.drop_column('payments_doctor', 'paddle_transaction_id')

    op.drop_index(
        'ix_subscription_plans_paddle_price_id',
        table_name='subscription_plans',
    )
    op.drop_column('subscription_plans', 'paddle_price_id')
