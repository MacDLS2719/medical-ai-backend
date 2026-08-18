from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalQuery(Base):
    __tablename__ = "medical_queries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    query_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="medical_queries"
    )

    query_pathologies = relationship(
        "MedicalQueryPathology",
        back_populates="query",
        cascade="all, delete-orphan"
    )

    query_sources = relationship(
        "MedicalQuerySource",
        back_populates="query",
        cascade="all, delete-orphan"
    )

    responses = relationship(
        "MedicalResponse",
        back_populates="query",
        cascade="all, delete-orphan"
    )