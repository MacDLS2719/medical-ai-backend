from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PatientLocation(Base):
    __tablename__ = "patient_locations"

    __table_args__ = (
        CheckConstraint(
            "last_lat >= -90 AND last_lat <= 90",
            name="ck_patient_locations_lat_range"
        ),
        CheckConstraint(
            "last_lng >= -180 AND last_lng <= 180",
            name="ck_patient_locations_lng_range"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    last_lat: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    last_lng: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    last_location_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="patient_location"
    )