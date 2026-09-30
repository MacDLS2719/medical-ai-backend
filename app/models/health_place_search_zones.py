from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class HealthPlaceSearchZone(Base):
    __tablename__ = "health_place_search_zones"

    __table_args__ = (
        UniqueConstraint(
            "zone_lat",
            "zone_lng",
            "ring_outer_km",
            name="uq_health_place_search_zones_zone_ring",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    zone_lat = Column(
        Float,
        nullable=False,
    )

    zone_lng = Column(
        Float,
        nullable=False,
    )

    ring_outer_km = Column(
        Float,
        nullable=False,
    )

    last_attempted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )