from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MedicalConversation(Base):
    __tablename__ = "medical_conversations"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doctor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    # ---------------------------------------------------------
    # Desactivación independiente de la conversación
    # ---------------------------------------------------------

    patient_deleted_at = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    doctor_deleted_at = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------------
    # Fechas
    # ---------------------------------------------------------

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ---------------------------------------------------------
    # Relaciones
    # ---------------------------------------------------------

    patient = relationship(
        "User",
        foreign_keys=[patient_id],
    )

    doctor = relationship(
        "User",
        foreign_keys=[doctor_id],
    )

    messages = relationship(
        "MedicalMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    video_calls = relationship(
        "MedicalVideoCall",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )