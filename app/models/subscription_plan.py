from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    # ==========================================================
    # IDENTIFICACIÓN
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # ==========================================================
    # INFORMACIÓN DEL PLAN
    # ==========================================================

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # PRECIO
    # ==========================================================

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0.00"),
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default=text("'USD'"),
    )

    billing_interval: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'month'"),
    )

    # ==========================================================
    # ESTADO DEL PLAN
    # ==========================================================

    is_free: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    # ==========================================================
    # FECHAS
    # ==========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ==========================================================
    # RELACIONES
    # ==========================================================

    doctor_subscriptions: Mapped[list["DoctorSubscription"]] = relationship(
        "DoctorSubscription",
        back_populates="subscription_plan",
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="plan",
    )

