from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalQuerySource(Base):
    __tablename__ = "medical_query_sources"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    query_id: Mapped[int] = mapped_column(
        ForeignKey("medical_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    query: Mapped["MedicalQuery"] = relationship(
        "MedicalQuery",
        back_populates="query_sources"
    )

    document: Mapped["MedicalDocument"] = relationship(
        "MedicalDocument",
        back_populates="query_sources"
    )
