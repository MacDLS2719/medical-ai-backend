from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalSearchUsage(Base):
    __tablename__ = "medical_search_usage"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subscription_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "doctor_subscriptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    search_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    search_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="now()",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="now()",
        onupdate=datetime.utcnow,
    )

    # Relaciones (sin back_populates para no modificar otros modelos)
    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    subscription = relationship(
        "DoctorSubscription",
        foreign_keys=[subscription_id],
    )