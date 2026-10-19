"""remove medical license from doctors

Revision ID: c7e0319db41a
Revises: f2a18b4c9d63
Create Date: 2026-10-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e0319db41a"
down_revision: Union[str, Sequence[str], None] = "f2a18b4c9d63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_doctors_medical_license", table_name="doctors")
    op.drop_column("doctors", "medical_license")


def downgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("medical_license", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_doctors_medical_license",
        "doctors",
        ["medical_license"],
        unique=True,
    )
