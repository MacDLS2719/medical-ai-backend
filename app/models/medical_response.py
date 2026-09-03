from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalResponse(Base):
    __tablename__ = "medical_responses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    query_id: Mapped[int] = mapped_column(
        ForeignKey("medical_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    response: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    query: Mapped["MedicalQuery"] = relationship(
        "MedicalQuery",
        back_populates="responses"
    )
