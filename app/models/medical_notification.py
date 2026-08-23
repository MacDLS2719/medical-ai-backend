from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    DateTime,
)

from sqlalchemy.sql import func

from app.core.database import Base


class MedicalNotification(Base):

    __tablename__ = "medical_notifications"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    frequency = Column(
        String(20),
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    data = Column(
        JSON,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )