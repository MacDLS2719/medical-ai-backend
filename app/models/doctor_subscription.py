from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorSubscription(Base):
    __tablename__ = "doctor_subscriptions"

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
    # RELACIONES
    # ==========================================================

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey(
            "doctors.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    subscription_plan_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subscription_plans.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # ESTADO
    # ==========================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'active'"),
        index=True,
    )

    # ==========================================================
    # PROVEEDOR DE PAGOS
    # ==========================================================

    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    provider_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    # ==========================================================
    # PERÍODO DE SUSCRIPCIÓN
    # ==========================================================

    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # ==========================================================
    # CANCELACIÓN
    # ==========================================================

    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
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

    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="subscriptions",
    )

    subscription_plan: Mapped["SubscriptionPlan"] = relationship(
        "SubscriptionPlan",
        back_populates="doctor_subscriptions",
    )