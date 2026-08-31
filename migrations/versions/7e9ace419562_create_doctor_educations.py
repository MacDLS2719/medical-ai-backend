"""create doctor educations

Revision ID: 8f3a21c9d745
Revises: 1666070f0e8b
Create Date: 2026-08-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ==========================================================
# REVISION IDENTIFIERS
# ==========================================================

revision: str = "8f3a21c9d745"

down_revision: Union[str, Sequence[str], None] = "1666070f0e8b"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ==========================================================
# UPGRADE
# ==========================================================

def upgrade() -> None:

    op.create_table(
        "doctor_educations",

        # --------------------------------------------------
        # ID
        # --------------------------------------------------

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),

        # --------------------------------------------------
        # RELACIÓN CON DOCTOR
        # --------------------------------------------------

        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey(
                "doctors.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        ),

        # --------------------------------------------------
        # INSTITUCIÓN
        # --------------------------------------------------

        sa.Column(
            "institution",
            sa.String(255),
            nullable=False,
        ),

        # --------------------------------------------------
        # TÍTULO / GRADO
        # --------------------------------------------------

        sa.Column(
            "degree",
            sa.String(150),
            nullable=False,
        ),

        # --------------------------------------------------
        # ÁREA DE ESTUDIO
        # --------------------------------------------------

        sa.Column(
            "field_of_study",
            sa.String(150),
            nullable=True,
        ),

        # --------------------------------------------------
        # AÑO DE INICIO
        # --------------------------------------------------

        sa.Column(
            "start_year",
            sa.Integer(),
            nullable=True,
        ),

        # --------------------------------------------------
        # AÑO DE FINALIZACIÓN
        # --------------------------------------------------

        sa.Column(
            "end_year",
            sa.Integer(),
            nullable=True,
        ),

        # --------------------------------------------------
        # DESCRIPCIÓN
        # --------------------------------------------------

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        # --------------------------------------------------
        # FECHAS
        # --------------------------------------------------

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


# ==========================================================
# DOWNGRADE
# ==========================================================

def downgrade() -> None:

    op.drop_table(
        "doctor_educations"
    )