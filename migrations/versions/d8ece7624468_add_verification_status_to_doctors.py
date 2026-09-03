"""add verification status to doctors

Revision ID: d8ece7624468
Revises: 42492911a436
Create Date: 2026-09-02 22:04:51.613024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8ece7624468'
down_revision: Union[str, Sequence[str], None] = '42492911a436'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column(
            "verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )

    op.create_index(
        "ix_doctors_verification_status",
        "doctors",
        ["verification_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_doctors_verification_status",
        table_name="doctors",
    )

    op.drop_column(
        "doctors",
        "verification_status",
    )