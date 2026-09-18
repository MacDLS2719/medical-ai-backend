"""create doctor reviews

Revision ID: 5ef3024ad32f
Revises: 67175e6620fc
Create Date: 2026-09-18 17:40:39.757674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5ef3024ad32f'
down_revision: Union[str, Sequence[str], None] = '67175e6620fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "doctor_reviews",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True
        ),

        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        ),

        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        ),

        sa.Column(
            "rating",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "comment",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            index=True
        ),

        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),

        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_doctor_reviews_rating"
        ),
    )


def downgrade():
    op.drop_table("doctor_reviews")