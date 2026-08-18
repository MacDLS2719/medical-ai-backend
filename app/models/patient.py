from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    document_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    gender: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
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

    user: Mapped["User"] = relationship(
        "User",
        back_populates="patient"
    )

    patient_pathologies: Mapped[list["PatientPathology"]] = relationship(
        "PatientPathology",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
