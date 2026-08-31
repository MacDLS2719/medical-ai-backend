from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorEducation(Base):
    __tablename__ = "doctor_educations"

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

    institution: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    degree: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    field_of_study: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    start_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    end_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
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

    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="educations"
    )