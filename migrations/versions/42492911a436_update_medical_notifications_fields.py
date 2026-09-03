"""update medical notifications fields

Revision ID: 42492911a436
Revises: 0b926799af69
Create Date: 2026-09-02 19:35:17.625196

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42492911a436"
down_revision: Union[str, Sequence[str], None] = "0b926799af69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================
    # AGREGAR NUEVOS CAMPOS TEMPORALMENTE NULLABLES
    # ==========================================================

    op.add_column(
        "medical_notifications",
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "medical_topic",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "information_type",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "source",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=True,
            server_default="active",
        ),
    )

    # ==========================================================
    # ACTUALIZAR REGISTROS EXISTENTES
    # ==========================================================

    op.execute(
        """
        UPDATE medical_notifications
        SET
            name = 'Alerta médica',
            medical_topic = 'General',
            information_type = 'research',
            source = 'medical',
            status = 'active'
        WHERE name IS NULL
        """
    )

    # ==========================================================
    # CONVERTIR CAMPOS A NOT NULL
    # ==========================================================

    op.alter_column(
        "medical_notifications",
        "name",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    op.alter_column(
        "medical_notifications",
        "medical_topic",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    op.alter_column(
        "medical_notifications",
        "information_type",
        existing_type=sa.String(length=100),
        nullable=False,
    )

    op.alter_column(
        "medical_notifications",
        "source",
        existing_type=sa.String(length=100),
        nullable=False,
    )

    op.alter_column(
        "medical_notifications",
        "status",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="active",
    )

    # ==========================================================
    # ELIMINAR CAMPOS ANTERIORES
    # ==========================================================

    op.drop_column(
        "medical_notifications",
        "title",
    )

    op.drop_column(
        "medical_notifications",
        "message",
    )

    op.drop_column(
        "medical_notifications",
        "is_read",
    )

    op.drop_column(
        "medical_notifications",
        "data",
    )

    op.drop_column(
        "medical_notifications",
        "type",
    )


def downgrade() -> None:

    # ==========================================================
    # RESTAURAR CAMPOS ANTERIORES
    # ==========================================================

    op.add_column(
        "medical_notifications",
        sa.Column(
            "type",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "message",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=True,
            server_default="false",
        ),
    )

    op.add_column(
        "medical_notifications",
        sa.Column(
            "data",
            sa.JSON(),
            nullable=True,
        ),
    )

    # ==========================================================
    # ELIMINAR NUEVOS CAMPOS
    # ==========================================================

    op.drop_column(
        "medical_notifications",
        "status",
    )

    op.drop_column(
        "medical_notifications",
        "source",
    )

    op.drop_column(
        "medical_notifications",
        "information_type",
    )

    op.drop_column(
        "medical_notifications",
        "medical_topic",
    )

    op.drop_column(
        "medical_notifications",
        "name",
    )