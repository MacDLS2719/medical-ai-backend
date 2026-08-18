from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("medical_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    abstract: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    publication_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    authors: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    document_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
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

    source: Mapped["MedicalSource"] = relationship(
        "MedicalSource",
        back_populates="documents"
    )

    query_sources: Mapped[list["MedicalQuerySource"]] = relationship(
        "MedicalQuerySource",
        back_populates="document",
        cascade="all, delete-orphan"
    )