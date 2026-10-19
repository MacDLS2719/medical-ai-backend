"""allow null doctor id in google profiles

Revision ID: d3e24f02d253
Revises: 2b406e16d542
Create Date: 2026-10-18 22:16:10.092397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e24f02d253'
down_revision: Union[str, Sequence[str], None] = '2b406e16d542'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "doctor_google_profiles",
        "doctor_id",
        nullable=True,
    )


def downgrade() -> None:
    # Antes de revertir, comprueba que no existan perfiles externos
    # con doctor_id NULL.
    op.alter_column(
        "doctor_google_profiles",
        "doctor_id",
        nullable=False,
    )
