"""create doctor subscriptions

Revision ID: 2e81f4d55376
Revises: 04a5246ea95d
Create Date: 2026-09-18 07:13:45.956728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e81f4d55376'
down_revision: Union[str, Sequence[str], None] = '04a5246ea95d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_table(
        "doctor_subscriptions",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "doctor_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "subscription_plan_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="active",
            index=True,
        ),

        # ======================================================
        # PROVEEDOR DE PAGOS
        # ======================================================

        sa.Column(
            "provider",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "provider_customer_id",
            sa.String(255),
            nullable=True,
            index=True,
        ),

        sa.Column(
            "provider_subscription_id",
            sa.String(255),
            nullable=True,
            unique=True,
            index=True,
        ),

        # ======================================================
        # PERÍODO DE SUSCRIPCIÓN
        # ======================================================

        sa.Column(
            "current_period_start",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "current_period_end",
            sa.DateTime(),
            nullable=True,
        ),

        # ======================================================
        # CANCELACIÓN
        # ======================================================

        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "cancelled_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "ended_at",
            sa.DateTime(),
            nullable=True,
        ),

        # ======================================================
        # FECHAS
        # ======================================================

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

        # ======================================================
        # FOREIGN KEYS
        # ======================================================

        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["subscription_plan_id"],
            ["subscription_plans.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_index(
        "ix_doctor_subscriptions_doctor_id",
        "doctor_subscriptions",
        ["doctor_id"],
    )

    op.create_index(
        "ix_doctor_subscriptions_subscription_plan_id",
        "doctor_subscriptions",
        ["subscription_plan_id"],
    )


def downgrade() -> None:
    op.drop_table("doctor_subscriptions")