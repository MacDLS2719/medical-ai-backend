"""add external health places and search zones

Revision ID: 9a495d424247
Revises: da4265168820
Create Date: 2026-09-29 21:25:31.921399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a495d424247"
down_revision: Union[str, Sequence[str], None] = "da4265168820"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================
    # external_health_places
    # ==========================================================

    op.create_table(
        "external_health_places",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "source",
            sa.String(),
            nullable=False,
            server_default="osm",
        ),

        sa.Column(
            "external_id",
            sa.String(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(),
            nullable=True,
        ),

        sa.Column(
            "kind",
            sa.String(),
            nullable=False,
        ),

        sa.Column(
            "lat",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "lng",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "address",
            sa.String(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "source",
            "external_id",
            name="uq_external_health_places_source_id",
        ),

        sa.CheckConstraint(
            "lat >= -90 AND lat <= 90",
            name="ck_external_health_places_lat_range",
        ),

        sa.CheckConstraint(
            "lng >= -180 AND lng <= 180",
            name="ck_external_health_places_lng_range",
        ),
    )

    # ==========================================================
    # health_place_search_zones
    # ==========================================================

    op.create_table(
        "health_place_search_zones",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "zone_lat",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "zone_lng",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "ring_outer_km",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "last_attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "zone_lat",
            "zone_lng",
            "ring_outer_km",
            name="uq_health_place_search_zones_zone_ring",
        ),
    )


def downgrade() -> None:

    op.drop_table("health_place_search_zones")

    op.drop_table("external_health_places")