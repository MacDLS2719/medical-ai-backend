"""add consultation type to medical appointments

Revision ID: c2a49e17d0b6
Revises: 773e59abf3c7
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2a49e17d0b6"
down_revision: Union[str, Sequence[str], None] = "773e59abf3c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medical_appointments",
        sa.Column(
            "consultation_type",
            sa.String(length=20),
            nullable=False,
            server_default="presencial",
        ),
    )


def downgrade() -> None:
    op.drop_column("medical_appointments", "consultation_type")