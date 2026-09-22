from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentDoctor(Base):
    __tablename__ = "payments_doctor"

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
    # RELACIÓN CON DOCTOR
    # ==========================================================

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey(
            "doctors.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # RELACIÓN CON SUSCRIPCIÓN
    # ==========================================================

    doctor_subscription_id: Mapped[int] = mapped_column(
        ForeignKey(
            "doctor_subscriptions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # STRIPE
    # ==========================================================

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )

    stripe_invoice_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    stripe_charge_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # PADDLE
    # ==========================================================

    paddle_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    paddle_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # INFORMACIÓN DEL PAGO
    # ==========================================================

    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # FECHA DE PAGO
    # ==========================================================

    paid_at: Mapped[datetime | None] = mapped_column(
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
        back_populates="payments",
    )

    doctor_subscription: Mapped["DoctorSubscription"] = relationship(
        "DoctorSubscription",
        back_populates="payments",
    )