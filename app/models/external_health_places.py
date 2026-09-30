import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    String,
    UUID,
    UniqueConstraint,
    func,
    Enum,
)

from app.core.database import Base
from .enums import HealthPlaceKind

class ExternalHealthPlace(Base):
    __tablename__ = "external_health_places"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_external_health_places_source_id",
        ),
        CheckConstraint(
            "lat >= -90 AND lat <= 90",
            name="ck_external_health_places_lat_range",
        ),
        CheckConstraint(
            "lng >= -180 AND lng <= 180",
            name="ck_external_health_places_lng_range",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source = Column(
        String,
        nullable=False,
        server_default="osm",
    )

    external_id = Column(
        String,
        nullable=False,
    )

    name = Column(
        String,
        nullable=True,
    )

    kind = Column(
        Enum(HealthPlaceKind, name="healthplacekind"),
        nullable=False,
    )

    lat = Column(
        Float,
        nullable=False,
    )

    lng = Column(
        Float,
        nullable=False,
    )

    address = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )