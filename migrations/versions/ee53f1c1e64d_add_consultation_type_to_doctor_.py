"""add consultation type to doctor availability

Revision ID: ee53f1c1e64d
Revises: 5ef3024ad32f
Create Date: 2026-09-18 17:47:45.711418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ee53f1c1e64d"
down_revision: Union[str, Sequence[str], None] = "5ef3024ad32f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ----------------------------------------------------------
    # MEDICAL DOCTOR AVAILABILITIES
    # ----------------------------------------------------------

    op.add_column(
        "medical_doctor_availabilities",
        sa.Column(
            "consultation_type",
            sa.String(length=20),
            nullable=False,
            server_default="presencial",
        ),
    )

    op.create_index(
        "ix_medical_doctor_availabilities_consultation_type",
        "medical_doctor_availabilities",
        ["consultation_type"],
        unique=False,
    )

    # ----------------------------------------------------------
    # MEDICAL DOCTOR AVAILABILITY EXCEPTIONS
    # ----------------------------------------------------------

    op.add_column(
        "medical_doctor_availability_exceptions",
        sa.Column(
            "consultation_type",
            sa.String(length=20),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_medical_doctor_availability_exceptions_consultation_type",
        "medical_doctor_availability_exceptions",
        ["consultation_type"],
        unique=False,
    )


def downgrade() -> None:

    # ----------------------------------------------------------
    # MEDICAL DOCTOR AVAILABILITY EXCEPTIONS
    # ----------------------------------------------------------

    op.drop_index(
        "ix_medical_doctor_availability_exceptions_consultation_type",
        table_name="medical_doctor_availability_exceptions",
    )

    op.drop_column(
        "medical_doctor_availability_exceptions",
        "consultation_type",
    )

    # ----------------------------------------------------------
    # MEDICAL DOCTOR AVAILABILITIES
    # ----------------------------------------------------------

    op.drop_index(
        "ix_medical_doctor_availabilities_consultation_type",
        table_name="medical_doctor_availabilities",
    )

    op.drop_column(
        "medical_doctor_availabilities",
        "consultation_type",
    )

