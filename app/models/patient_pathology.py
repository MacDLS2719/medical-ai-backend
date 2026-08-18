from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PatientPathology(Base):
    __tablename__ = "patient_pathologies"

    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "pathology_id",
            name="uq_patient_pathology"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    pathology_id: Mapped[int] = mapped_column(
        ForeignKey("pathologies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    diagnosis_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active"
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="patient_pathologies"
    )

    pathology: Mapped["Pathology"] = relationship(
        "Pathology",
        back_populates="patient_pathologies"
    )