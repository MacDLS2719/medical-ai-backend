from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MedicalAppointment(Base):

    __tablename__ = "medical_appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    appointment_date = Column(
        Date,
        nullable=False,
        index=True
    )

    appointment_time = Column(
        Time,
        nullable=False,
        index=True
    )

    status = Column(
        String(30),
        nullable=False,
        default="scheduled",
        index=True
    )

    location = Column(
        String(255),
        nullable=True
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

    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = relationship(
        "User",
        foreign_keys=[doctor_id]
    )

    status_history = relationship(
        "MedicalAppointmentStatusHistory",
        back_populates="appointment",
        cascade="all, delete-orphan"
    )