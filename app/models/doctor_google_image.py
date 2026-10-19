
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorGoogleImage(Base):
    __tablename__ = "doctor_google_images"

    __table_args__ = (
        CheckConstraint(
            "image_order >= 1 AND image_order <= 3",
            name="ck_doctor_google_images_order_range",
        ),
        UniqueConstraint(
            "google_profile_id",
            "image_order",
            name="uq_doctor_google_images_profile_order",
        ),
        CheckConstraint(
            "image_url IS NOT NULL OR image_path IS NOT NULL",
            name="ck_doctor_google_images_has_location",
        ),
        Index(
            "ix_doctor_google_images_google_profile_id",
            "google_profile_id",
        ),
    )

    # Identificación
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Perfil de Google asociado
    google_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "doctor_google_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # Ubicación de la imagen
    image_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
    )

    image_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )

    # Posición visible: 1, 2 o 3
    image_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    # Relación con el perfil
    google_profile = relationship(
        "DoctorGoogleProfile",
        back_populates="images",
    )
