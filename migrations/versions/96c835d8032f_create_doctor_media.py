"""create doctor media

Revision ID: 4c7e91b2a563
Revises: 8f3a21c9d745
Create Date: 2026-08-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ==========================================================
# REVISION IDENTIFIERS
# ==========================================================

revision: str = "4c7e91b2a563"

down_revision: Union[str, Sequence[str], None] = "8f3a21c9d745"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ==========================================================
# UPGRADE
# ==========================================================

def upgrade() -> None:

    op.create_table(
        "doctor_media",

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
        # TIPO DE ARCHIVO
        # --------------------------------------------------

        sa.Column(
            "media_type",
            sa.String(50),
            nullable=False,
        ),

        # --------------------------------------------------
        # URL / RUTA DEL ARCHIVO
        # --------------------------------------------------

        sa.Column(
            "file_url",
            sa.String(500),
            nullable=False,
        ),

        # --------------------------------------------------
        # NOMBRE ORIGINAL DEL ARCHIVO
        # --------------------------------------------------

        sa.Column(
            "file_name",
            sa.String(255),
            nullable=True,
        ),

        # --------------------------------------------------
        # MIME TYPE
        # --------------------------------------------------

        sa.Column(
            "mime_type",
            sa.String(100),
            nullable=True,
        ),

        # --------------------------------------------------
        # ESTADO
        # --------------------------------------------------

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        "doctor_media"
    )