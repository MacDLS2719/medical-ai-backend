
"""create doctor google images

Revision ID: 2b406e16d542
Revises: 7c27ad9acc9a
Create Date: 2026-10-18 20:24:40.848202
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2b406e16d542"
down_revision: Union[str, Sequence[str], None] = "7c27ad9acc9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create doctor_google_images table."""

    op.create_table(
        "doctor_google_images",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "google_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "doctor_google_profiles.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "image_url",
            sa.String(length=2048),
            nullable=True,
        ),
        sa.Column(
            "image_path",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "image_order",
            sa.SmallInteger(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "image_order >= 1 AND image_order <= 3",
            name="ck_doctor_google_images_order_range",
        ),
        sa.UniqueConstraint(
            "google_profile_id",
            "image_order",
            name="uq_doctor_google_images_profile_order",
        ),
        sa.CheckConstraint(
            "image_url IS NOT NULL OR image_path IS NOT NULL",
            name="ck_doctor_google_images_has_location",
        ),
    )

    op.create_index(
        "ix_doctor_google_images_google_profile_id",
        "doctor_google_images",
        ["google_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop doctor_google_images table."""

    op.drop_index(
        "ix_doctor_google_images_google_profile_id",
        table_name="doctor_google_images",
    )

    op.drop_table("doctor_google_images")

