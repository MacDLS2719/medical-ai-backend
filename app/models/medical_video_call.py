
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class MedicalVideoCall(Base):
    __tablename__ = "medical_video_calls"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    conversation_id = Column(
        Integer,
        ForeignKey(
            "medical_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    caller_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    receiver_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------
    # Daily.co
    # ---------------------------------------------------------

    room_name = Column(
        String(255),
        nullable=False,
    )

    room_url = Column(
        String(1000),
        nullable=True,
    )

    # ---------------------------------------------------------
    # Estado de la llamada
    # ---------------------------------------------------------

    status = Column(
        String(30),
        nullable=False,
        default="calling",
        server_default="calling",
        index=True,
    )

    # ---------------------------------------------------------
    # Control temporal
    # ---------------------------------------------------------

    started_at = Column(
        DateTime,
        nullable=True,
    )

    ended_at = Column(
        DateTime,
        nullable=True,
    )

    duration = Column(
        Integer,
        nullable=True,
    )

    # ---------------------------------------------------------
    # Fechas del registro
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

    conversation = relationship(
        "MedicalConversation",
        back_populates="video_calls",
    )

    caller = relationship(
        "User",
        foreign_keys=[caller_id],
    )

    receiver = relationship(
        "User",
        foreign_keys=[receiver_id],
    )