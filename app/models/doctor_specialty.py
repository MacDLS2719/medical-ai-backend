from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorSpecialty(Base):
    __tablename__ = "doctor_specialties"

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "specialty_id",
            name="uq_doctor_specialty"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialties.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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

    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="doctor_specialties"
    )

    specialty: Mapped["Specialty"] = relationship(
        "Specialty",
        back_populates="doctor_specialties"
    )