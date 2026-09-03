from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalQueryPathology(Base):
    __tablename__ = "medical_query_pathologies"

    __table_args__ = (
        UniqueConstraint(
            "query_id",
            "pathology_id",
            name="uq_medical_query_pathology"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    query_id: Mapped[int] = mapped_column(
        ForeignKey("medical_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    pathology_id: Mapped[int] = mapped_column(
        ForeignKey("pathologies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    query: Mapped["MedicalQuery"] = relationship(
        "MedicalQuery",
        back_populates="query_pathologies"
    )

    pathology: Mapped["Pathology"] = relationship(
        "Pathology",
        back_populates="medical_query_pathologies"
    )
