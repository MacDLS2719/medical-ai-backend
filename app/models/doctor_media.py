from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.encryption import EncryptedString


class DoctorMedia(Base):
    __tablename__ = "doctor_media"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey(
            "doctors.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    media_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    file_url: Mapped[str] = mapped_column(
        EncryptedString(500),
        nullable=False
    )

    file_name: Mapped[str | None] = mapped_column(
        EncryptedString(255),
        nullable=True
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(100),
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

    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="media"
    )
