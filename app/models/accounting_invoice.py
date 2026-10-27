
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AccountingInvoice(Base):
    __tablename__ = "accounting_invoices"

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "invoice_number",
            name="uq_accounting_invoices_doctor_number",
        ),
        CheckConstraint(
            "subtotal >= 0 AND tax_amount >= 0 AND total_amount >= 0",
            name="ck_accounting_invoices_amounts",
        ),
        CheckConstraint(
            "status IN ('draft', 'issued', 'paid', 'void', 'refunded')",
            name="ck_accounting_invoices_status",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    doctor_id = Column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    patient_id = Column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    appointment_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    invoice_number = Column(
        String(100),
        nullable=False,
    )

    subtotal = Column(
        Numeric(12, 2),
        nullable=False,
    )

    tax_amount = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    total_amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    currency = Column(
        String(3),
        nullable=False,
    )

    status = Column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    issued_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    due_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    transactions = relationship(
        "AccountingTransaction",
        back_populates="invoice",
    )

    attachments = relationship(
        "AccountingAttachment",
        back_populates="invoice",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
