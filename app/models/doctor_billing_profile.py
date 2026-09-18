from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DoctorBillingProfile(Base):
    __tablename__ = "doctor_billing_profiles"

    # ==========================================================
    # IDENTIFICACIÓN
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey(
            "doctors.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    # ==========================================================
    # INFORMACIÓN DE FACTURACIÓN
    # ==========================================================

    billing_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    billing_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ==========================================================
    # DIRECCIÓN DE FACTURACIÓN
    # ==========================================================

    billing_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    billing_address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    billing_city: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    billing_state: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    billing_postal_code: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # ==========================================================
    # INFORMACIÓN FISCAL
    # ==========================================================

    tax_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tax_id_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
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

    # ==========================================================
    # MÉTODO DE PAGO
    # ==========================================================

    payment_method_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    payment_method_brand: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    payment_method_last4: Mapped[str | None] = mapped_column(
        String(4),
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
    # RELACIÓN CON DOCTOR
    # ==========================================================

    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="billing_profile",
    )