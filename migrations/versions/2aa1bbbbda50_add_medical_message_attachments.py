"""add medical message attachments

Revision ID: 2aa1bbbbda50
Revises: 4c7e91b2a563
Create Date: 2026-08-29 21:45:50.261123

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2aa1bbbbda50'
down_revision: Union[str, Sequence[str], None] = '4c7e91b2a563'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create medical_message_attachments table."""

    op.create_table(
        'medical_message_attachments',

        # ==========================================================
        # ID
        # ==========================================================
        sa.Column(
            'id',
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),

        # ==========================================================
        # RELACIÓN CON MEDICAL_MESSAGES
        # ==========================================================
        sa.Column(
            'message_id',
            sa.Integer(),
            nullable=False,
        ),

        # ==========================================================
        # INFORMACIÓN DEL ARCHIVO
        # ==========================================================
        sa.Column(
            'file_name',
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            'file_path',
            sa.String(length=500),
            nullable=False,
        ),

        # URL del archivo.
        # Será NULL inicialmente porque utilizaremos
        # almacenamiento local.
        sa.Column(
            'file_url',
            sa.String(length=1000),
            nullable=True,
        ),

        # Ejemplo:
        # audio/webm
        # audio/mpeg
        # audio/wav
        # audio/mp4
        sa.Column(
            'mime_type',
            sa.String(length=100),
            nullable=False,
        ),

        # Tamaño del archivo en bytes
        sa.Column(
            'file_size',
            sa.BigInteger(),
            nullable=True,
        ),

        # Duración del audio en segundos
        sa.Column(
            'duration',
            sa.Float(),
            nullable=True,
        ),

        # ==========================================================
        # ALMACENAMIENTO
        # ==========================================================
        # Inicialmente:
        # local
        #
        # Posteriormente:
        # s3
        # etc.
        sa.Column(
            'storage_disk',
            sa.String(length=50),
            nullable=False,
            server_default='local',
        ),

        # Tipo de adjunto.
        # Inicialmente utilizaremos:
        # audio
        #
        # En el futuro podemos utilizar:
        # image
        # document
        # pdf
        # etc.
        sa.Column(
            'attachment_type',
            sa.String(length=50),
            nullable=False,
            server_default='audio',
        ),

        # ==========================================================
        # FECHAS
        # ==========================================================
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),

        # ==========================================================
        # FOREIGN KEY
        # ==========================================================
        sa.ForeignKeyConstraint(
            ['message_id'],
            ['medical_messages.id'],
            ondelete='CASCADE',
        ),
    )

    # ==============================================================
    # ÍNDICE
    # ==============================================================
    op.create_index(
        'ix_medical_message_attachments_message_id',
        'medical_message_attachments',
        ['message_id'],
    )


def downgrade() -> None:
    """Drop medical_message_attachments table."""

    op.drop_index(
        'ix_medical_message_attachments_message_id',
        table_name='medical_message_attachments',
    )

    op.drop_table(
        'medical_message_attachments'
    )
