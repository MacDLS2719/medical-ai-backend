
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorGoogleProfile(Base):
    __tablename__ = "doctor_google_profiles"

    __table_args__ = (
        CheckConstraint(
            "google_rating IS NULL OR "
            "(google_rating >= 0 AND google_rating <= 5)",
            name="ck_doctor_google_profiles_rating_range",
        ),
        CheckConstraint(
            "google_reviews_count IS NULL OR google_reviews_count >= 0",
            name="ck_doctor_google_profiles_reviews_nonnegative",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_doctor_google_profiles_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_doctor_google_profiles_longitude_range",
        ),
        Index(
            "ix_doctor_google_profiles_google_place_id",
            "google_place_id",
        ),
    )

    # Identificación
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Relación con el médico: doctors.id es INTEGER
    doctor_id: Mapped[Optional[int]] = mapped_column(
    Integer,
    ForeignKey("doctors.id", ondelete="CASCADE"),
    nullable=True,
    unique=True,
    index=False,
)

    # Información del perfil de Google
    google_place_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    google_category: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    google_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=2, scale=1),
        nullable=True,
    )

    google_reviews_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    phone_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    formatted_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Coordenadas geográficas
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=7),
        nullable=True,
    )

    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=7),
        nullable=True,
    )

    # Horarios estructurados en formato JSON
    opening_hours: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Enlaces públicos
    booking_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
    )

    google_maps_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
    )

    website_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
    )

    # Verificación y sincronización
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relaciones
    doctor = relationship(
        "Doctor",
        back_populates="google_profile",
    )

    images = relationship(
        "DoctorGoogleImage",
        back_populates="google_profile",
        cascade="all, delete-orphan",
        order_by="DoctorGoogleImage.image_order",
        passive_deletes=True,
    )
