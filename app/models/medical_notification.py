from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
)

from sqlalchemy.sql import func

from app.core.database import Base


class MedicalNotification(Base):

    __tablename__ = "medical_notifications"

    # ==========================================================
    # IDENTIFICADOR
    # ==========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ==========================================================
    # USUARIO
    # ==========================================================

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # INFORMACIÓN DE LA ALERTA
    # ==========================================================

    name = Column(
        String(255),
        nullable=False,
    )

    medical_topic = Column(
        String(255),
        nullable=False,
        index=True,
    )

    information_type = Column(
        String(100),
        nullable=False,
        index=True,
    )

    frequency = Column(
        String(20),
        nullable=False,
    )

    source = Column(
        String(100),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # ESTADO
    # ==========================================================

    status = Column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )

    # ==========================================================
    # FECHAS
    # ==========================================================

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