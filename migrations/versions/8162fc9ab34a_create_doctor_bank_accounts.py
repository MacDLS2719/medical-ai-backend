"""create doctor bank accounts

Revision ID: <REVISION_GENERADA>
Revises: 99cde91189d3
Create Date: 2026-09-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "<REVISION_GENERADA>"
down_revision: Union[str, Sequence[str], None] = "99cde91189d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctor_bank_accounts",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "doctor_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "account_holder",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "bank_name",
            sa.String(100),
            nullable=False,
        ),

        sa.Column(
            "account_type",
            sa.String(50),
            nullable=False,
        ),

        sa.Column(
            "account_number",
            sa.String(100),
            nullable=False,
        ),

        sa.Column(
            "country",
            sa.String(100),
            nullable=False,
        ),

        sa.Column(
            "currency",
            sa.String(10),
            nullable=False,
        ),

        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_doctor_bank_accounts_doctor_id",
        "doctor_bank_accounts",
        ["doctor_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_doctor_bank_accounts_doctor_id",
        table_name="doctor_bank_accounts",
    )

    op.drop_table(
        "doctor_bank_accounts",
    )