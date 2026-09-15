"""add independent chat deactivation

Revision ID: 8353eabaa011
Revises: 92b3918cef02
Create Date: 2026-09-15 12:24:52.524814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8353eabaa011'
down_revision: Union[str, Sequence[str], None] = '92b3918cef02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medical_conversations",
        sa.Column(
            "patient_deleted_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.add_column(
        "medical_conversations",
        sa.Column(
            "doctor_deleted_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_medical_conversations_patient_deleted_at",
        "medical_conversations",
        ["patient_deleted_at"],
        unique=False,
    )

    op.create_index(
        "ix_medical_conversations_doctor_deleted_at",
        "medical_conversations",
        ["doctor_deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medical_conversations_doctor_deleted_at",
        table_name="medical_conversations",
    )

    op.drop_index(
        "ix_medical_conversations_patient_deleted_at",
        table_name="medical_conversations",
    )

    op.drop_column(
        "medical_conversations",
        "doctor_deleted_at",
    )

    op.drop_column(
        "medical_conversations",
        "patient_deleted_at",
    )