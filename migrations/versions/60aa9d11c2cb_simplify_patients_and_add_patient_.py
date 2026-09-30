"""simplify patients and add patient locations

Revision ID: 60aa9d11c2cb
Revises: 32409ad0ad06
Create Date: 2026-09-29 21:08:04.852382

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60aa9d11c2cb'
down_revision: Union[str, Sequence[str], None] = '32409ad0ad06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Crear tabla de ubicación del paciente
    op.create_table(
        "patient_locations",

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "last_lat",
            sa.Float(),
            nullable=False
        ),

        sa.Column(
            "last_lng",
            sa.Float(),
            nullable=False
        ),

        sa.Column(
            "last_location_at",
            sa.DateTime(timezone=True),
            nullable=False
        ),

        sa.CheckConstraint(
            "last_lat >= -90 AND last_lat <= 90",
            name="ck_patient_locations_lat_range"
        ),

        sa.CheckConstraint(
            "last_lng >= -180 AND last_lng <= 180",
            name="ck_patient_locations_lng_range"
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE"
        ),

        sa.PrimaryKeyConstraint("user_id")
    )


def downgrade() -> None:

    op.drop_table("patient_locations")
