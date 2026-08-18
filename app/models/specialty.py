from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    doctor_specialties: Mapped[list["DoctorSpecialty"]] = relationship(
        "DoctorSpecialty",
        back_populates="specialty",
        cascade="all, delete-orphan"
    )