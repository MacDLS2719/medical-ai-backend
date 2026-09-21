"""create payments doctor

Revision ID: d0909cc9cda5
Revises: ee53f1c1e64d
Create Date: 2026-09-21 13:48:38.227113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd0909cc9cda5'
down_revision: Union[str, Sequence[str], None] = 'ee53f1c1e64d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments_doctor",

        # ==========================================================
        # IDENTIFICACIÓN
        # ==========================================================

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),

        # ==========================================================
        # RELACIÓN CON DOCTOR
        # ==========================================================

        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey(
                "doctors.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        # ==========================================================
        # RELACIÓN CON SUSCRIPCIÓN
        # ==========================================================

        sa.Column(
            "doctor_subscription_id",
            sa.Integer(),
            sa.ForeignKey(
                "doctor_subscriptions.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        # ==========================================================
        # STRIPE
        # ==========================================================

        sa.Column(
            "stripe_payment_intent_id",
            sa.String(255),
            nullable=True,
            unique=True,
        ),

        sa.Column(
            "stripe_invoice_id",
            sa.String(255),
            nullable=True,
            index=True,
        ),

        sa.Column(
            "stripe_charge_id",
            sa.String(255),
            nullable=True,
            index=True,
        ),

        # ==========================================================
        # INFORMACIÓN DEL PAGO
        # ==========================================================

        sa.Column(
            "amount",
            sa.Numeric(10, 2),
            nullable=False,
        ),

        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),

        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            index=True,
        ),

        # ==========================================================
        # FECHA DE PAGO
        # ==========================================================

        sa.Column(
            "paid_at",
            sa.DateTime(),
            nullable=True,
        ),

        # ==========================================================
        # FECHAS
        # ==========================================================

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

    # Índices
    op.create_index(
        "ix_payments_doctor_doctor_id",
        "payments_doctor",
        ["doctor_id"],
    )

    op.create_index(
        "ix_payments_doctor_doctor_subscription_id",
        "payments_doctor",
        ["doctor_subscription_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payments_doctor_doctor_subscription_id",
        table_name="payments_doctor",
    )

    op.drop_index(
        "ix_payments_doctor_doctor_id",
        table_name="payments_doctor",
    )

    op.drop_table("payments_doctor")
