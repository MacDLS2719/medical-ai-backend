from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base



class MedicalMessageAttachment(Base):
    __tablename__ = "medical_message_attachments"

    # ==========================================================
    # ID
    # ==========================================================
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ==========================================================
    # RELACIÓN CON MEDICAL_MESSAGES
    # ==========================================================
    message_id: Mapped[int] = mapped_column(
        ForeignKey(
            "medical_messages.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # INFORMACIÓN DEL ARCHIVO
    # ==========================================================
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Duración del audio en segundos
    duration: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ==========================================================
    # ALMACENAMIENTO
    # ==========================================================
    # local / s3 / etc.
    storage_disk: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="local",
        server_default="local",
    )

    # audio / image / document / pdf / etc.
    attachment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="audio",
        server_default="audio",
    )

    # ==========================================================
    # FECHAS
    # ==========================================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="now()",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default="now()",
    )

    # ==========================================================
    # RELACIÓN ORM
    # ==========================================================
    message = relationship(
        "MedicalMessage",
        back_populates="attachments",
    )
