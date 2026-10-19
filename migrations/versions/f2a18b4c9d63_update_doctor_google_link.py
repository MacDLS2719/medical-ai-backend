"""replace doctor registration fields with Google link

Revision ID: f2a18b4c9d63
Revises: 4ebd2d9c1a70
Create Date: 2026-10-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a18b4c9d63"
down_revision: Union[str, Sequence[str], None] = "4ebd2d9c1a70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("doctors", "professional_registration_number")
    op.drop_column("doctors", "professional_college")
    op.add_column(
        "doctors",
        sa.Column("linkgoogle", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("doctors", "linkgoogle")
    op.add_column(
        "doctors",
        sa.Column("professional_college", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "doctors",
        sa.Column("professional_registration_number", sa.String(length=100), nullable=True),
    )
