"""create doctor billing profiles

Revision ID: 67175e6620fc
Revises: 2e81f4d55376
Create Date: 2026-09-18 07:14:16.647734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67175e6620fc'
down_revision: Union[str, Sequence[str], None] = '2e81f4d55376'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctor_billing_profiles",

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
            unique=True,
        ),

        # ======================================================
        # INFORMACIÓN DE FACTURACIÓN
        # ======================================================

        sa.Column(
            "billing_name",
            sa.String(255),
            nullable=True,
        ),

        sa.Column(
            "billing_email",
            sa.String(255),
            nullable=True,
        ),

        # ======================================================
        # DIRECCIÓN DE FACTURACIÓN
        # ======================================================

        sa.Column(
            "billing_country",
            sa.String(100),
            nullable=True,
        ),

        sa.Column(
            "billing_address",
            sa.String(255),
            nullable=True,
        ),

        sa.Column(
            "billing_city",
            sa.String(150),
            nullable=True,
        ),

        sa.Column(
            "billing_state",
            sa.String(150),
            nullable=True,
        ),

        sa.Column(
            "billing_postal_code",
            sa.String(30),
            nullable=True,
        ),

        # ======================================================
        # INFORMACIÓN FISCAL
        # ======================================================

        sa.Column(
            "tax_id",
            sa.String(100),
            nullable=True,
        ),

        sa.Column(
            "tax_id_type",
            sa.String(50),
            nullable=True,
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

        # ======================================================
        # MÉTODO DE PAGO
        # ======================================================

        sa.Column(
            "payment_method_type",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "payment_method_brand",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "payment_method_last4",
            sa.String(4),
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
        # FOREIGN KEY
        # ======================================================

        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("doctor_billing_profiles")