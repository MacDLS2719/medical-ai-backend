from sqlalchemy import Column, Integer, String, Text, Boolean, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MedicalDoctorAvailabilityException(Base):

    __tablename__ = "medical_doctor_availability_exceptions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    exception_date = Column(
        Date,
        nullable=False,
        index=True
    )

    start_time = Column(
        Time,
        nullable=True
    )

    end_time = Column(
        Time,
        nullable=True
    )

    type = Column(
        String(50),
        nullable=False,
        default="unavailable"
    )

    reason = Column(
        Text,
        nullable=True
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------

    doctor = relationship(
        "User",
        foreign_keys=[doctor_id]
    )
