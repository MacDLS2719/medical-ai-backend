from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalSource(Base):
    __tablename__ = "medical_sources"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    base_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    api_url: Mapped[str | None] = mapped_column(
        String(500),
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

    documents: Mapped[list["MedicalDocument"]] = relationship(
        "MedicalDocument",
        back_populates="source",
        cascade="all, delete-orphan"
    )