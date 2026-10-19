
"""create doctor google profiles

Revision ID: 7c27ad9acc9a
Revises: c7e0319db41a
Create Date: 2026-10-18 20:24:22.055601
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7c27ad9acc9a"
down_revision: Union[str, Sequence[str], None] = "c7e0319db41a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create doctor_google_profiles table."""

    op.create_table(
        "doctor_google_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doctor_id",
            sa.Integer(),  # Correcto: doctors.id es INTEGER (int4)
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "google_place_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "business_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "google_category",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "google_rating",
            sa.Numeric(precision=2, scale=1),
            nullable=True,
        ),
        sa.Column(
            "google_reviews_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "phone_number",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "formatted_address",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "opening_hours",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "booking_url",
            sa.String(length=2048),
            nullable=True,
        ),
        sa.Column(
            "google_maps_url",
            sa.String(length=2048),
            nullable=True,
        ),
        sa.Column(
            "website_url",
            sa.String(length=2048),
            nullable=True,
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            "google_rating IS NULL OR "
            "(google_rating >= 0 AND google_rating <= 5)",
            name="ck_doctor_google_profiles_rating_range",
        ),
        sa.CheckConstraint(
            "google_reviews_count IS NULL OR google_reviews_count >= 0",
            name="ck_doctor_google_profiles_reviews_nonnegative",
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_doctor_google_profiles_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_doctor_google_profiles_longitude_range",
        ),
    )

    op.create_index(
        "ix_doctor_google_profiles_google_place_id",
        "doctor_google_profiles",
        ["google_place_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop doctor_google_profiles table."""

    op.drop_index(
        "ix_doctor_google_profiles_google_place_id",
        table_name="doctor_google_profiles",
    )

    op.drop_table("doctor_google_profiles")
