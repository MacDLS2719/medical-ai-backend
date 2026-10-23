"""add languages and insurance company to doctors

Revision ID: 06dd7454551f
Revises: c3527749d531
Create Date: 2026-10-22 19:37:49.940770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '06dd7454551f'
down_revision: Union[str, Sequence[str], None] = 'c3527749d531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column(
            "languages",
            postgresql.JSONB(),
            nullable=True,
        ),
    )

    op.add_column(
        "doctors",
        sa.Column(
            "insurance_company",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("doctors", "insurance_company")
    op.drop_column("doctors", "languages")
