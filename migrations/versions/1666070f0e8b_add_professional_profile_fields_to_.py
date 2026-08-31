"""add professional profile fields to doctors

Revision ID: 1666070f0e8b
Revises: 667482117c47
Create Date: 2026-08-29 15:06:31.990275

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ==========================================================
# REVISION IDENTIFIERS
# ==========================================================

revision: str = "1666070f0e8b"

down_revision: Union[str, Sequence[str], None] = "667482117c47"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ==========================================================
# UPGRADE
# ==========================================================

def upgrade() -> None:

    # ------------------------------------------------------
    # BIOGRAFÍA / DESCRIPCIÓN DEL MÉDICO
    # ------------------------------------------------------

    op.add_column(
        "doctors",
        sa.Column(
            "bio",
            sa.Text(),
            nullable=True,
        ),
    )

    # ------------------------------------------------------
    # EXPERIENCIA PROFESIONAL
    # ------------------------------------------------------

    op.add_column(
        "doctors",
        sa.Column(
            "experience",
            sa.Text(),
            nullable=True,
        ),
    )


# ==========================================================
# DOWNGRADE
# ==========================================================

def downgrade() -> None:

    # ------------------------------------------------------
    # ELIMINAR EXPERIENCIA PROFESIONAL
    # ------------------------------------------------------

    op.drop_column(
        "doctors",
        "experience",
    )

    # ------------------------------------------------------
    # ELIMINAR BIOGRAFÍA
    # ------------------------------------------------------

    op.drop_column(
        "doctors",
        "bio",
    )