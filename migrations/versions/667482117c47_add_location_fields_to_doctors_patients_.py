"""add location fields to doctors patients and availabilities

Revision ID: 667482117c47
Revises: 0a3765c884c7
Create Date: 2026-08-25 21:16:36.821787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '667482117c47'
down_revision: Union[str, Sequence[str], None] = '0a3765c884c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================
    # DOCTORS
    # ==========================================================

    op.add_column("doctors", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("doctors", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("doctors", sa.Column("longitude", sa.Float(), nullable=True))

    op.create_check_constraint(
        "ck_doctors_latitude_range",
        "doctors",
        "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)"
    )
    op.create_check_constraint(
        "ck_doctors_longitude_range",
        "doctors",
        "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)"
    )

    # ==========================================================
    # PATIENTS
    # ==========================================================

    op.add_column("patients", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("patients", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("patients", sa.Column("longitude", sa.Float(), nullable=True))

    op.create_check_constraint(
        "ck_patients_latitude_range",
        "patients",
        "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)"
    )
    op.create_check_constraint(
        "ck_patients_longitude_range",
        "patients",
        "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)"
    )

    # ==========================================================
    # MEDICAL_DOCTOR_AVAILABILITIES
    # ==========================================================

    op.add_column(
        "medical_doctor_availabilities",
        sa.Column("address", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:

    op.drop_column("medical_doctor_availabilities", "address")

    op.drop_constraint("ck_patients_longitude_range", "patients", type_="check")
    op.drop_constraint("ck_patients_latitude_range", "patients", type_="check")
    op.drop_column("patients", "longitude")
    op.drop_column("patients", "latitude")
    op.drop_column("patients", "address")

    op.drop_constraint("ck_doctors_longitude_range", "doctors", type_="check")
    op.drop_constraint("ck_doctors_latitude_range", "doctors", type_="check")
    op.drop_column("doctors", "longitude")
    op.drop_column("doctors", "latitude")
    op.drop_column("doctors", "address")