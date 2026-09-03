"""create medical verifications table

Revision ID: 92b3918cef02
Revises: d8ece7624468
Create Date: 2026-09-02 22:07:54.511505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92b3918cef02'
down_revision: Union[str, Sequence[str], None] = 'd8ece7624468'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medical_verifications",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            index=True,
        ),

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

        sa.Column(
            "verifier_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
            ),
            nullable=True,
            index=True,
        ),

        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),

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

    op.create_index(
        "ix_medical_verifications_status",
        "medical_verifications",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medical_verifications_status",
        table_name="medical_verifications",
    )

    op.drop_table("medical_verifications")