"""remove patient pathology tables

Revision ID: da4265168820
Revises: 60aa9d11c2cb
Create Date: 2026-09-29 21:11:04.587429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da4265168820'
down_revision: Union[str, Sequence[str], None] = '60aa9d11c2cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Primero eliminamos las tablas que dependen de pathologies
    op.drop_table("patient_pathologies")
    op.drop_table("medical_query_pathologies")

    # Finalmente eliminamos la tabla principal
    op.drop_table("pathologies")


def downgrade() -> None:
    pass
