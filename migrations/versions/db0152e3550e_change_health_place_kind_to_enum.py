"""change health place kind to enum

Revision ID: db0152e3550e
Revises: 9a495d424247
Create Date: 2026-09-29 21:48:19.622428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "db0152e3550e"
down_revision: Union[str, Sequence[str], None] = "9a495d424247"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear ENUM en PostgreSQL
    healthplacekind = postgresql.ENUM(
        "hospital",
        "clinic",
        "pharmacy",
        name="healthplacekind",
    )

    healthplacekind.create(op.get_bind(), checkfirst=True)

    # Convertir la columna de VARCHAR a ENUM
    op.alter_column(
        "external_health_places",
        "kind",
        existing_type=sa.String(),
        type_=healthplacekind,
        existing_nullable=False,
        postgresql_using="kind::healthplacekind",
    )


def downgrade() -> None:
    # Volver de ENUM a VARCHAR
    op.alter_column(
        "external_health_places",
        "kind",
        existing_type=postgresql.ENUM(
            "hospital",
            "clinic",
            "pharmacy",
            name="healthplacekind",
        ),
        type_=sa.String(),
        existing_nullable=False,
        postgresql_using="kind::text",
    )

    # Eliminar ENUM de PostgreSQL
    healthplacekind = postgresql.ENUM(
        "hospital",
        "clinic",
        "pharmacy",
        name="healthplacekind",
    )

    healthplacekind.drop(op.get_bind(), checkfirst=True)