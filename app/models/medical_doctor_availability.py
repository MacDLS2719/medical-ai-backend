from sqlalchemy import Column, Integer, Time, Boolean, DateTime, ForeignKey, Date, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MedicalDoctorAvailability(Base):

    __tablename__ = "medical_doctor_availabilities"

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

    day_of_week = Column(
        Integer,
        nullable=True,
        index=True
    )

    start_date = Column(
        Date,
        nullable=True,
        index=True
    )

    end_date = Column(
        Date,
        nullable=True,
        index=True
    )

    start_time = Column(
        Time,
        nullable=False
    )

    end_time = Column(
        Time,
        nullable=False
    )

    slot_duration = Column(
        Integer,
        nullable=False,
        default=30
    )

    address = Column(
        String(255),
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
