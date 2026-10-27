
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AccountingAttachment(Base):
    __tablename__ = "accounting_attachments"

    __table_args__ = (
        CheckConstraint(
            "(invoice_id IS NOT NULL AND expense_id IS NULL) OR "
            "(invoice_id IS NULL AND expense_id IS NOT NULL)",
            name="ck_accounting_attachments_one_parent",
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

    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounting_invoices.id", ondelete="CASCADE"),
        nullable=True,
    )

    expense_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounting_expenses.id", ondelete="CASCADE"),
        nullable=True,
    )

    file_url = Column(
        Text,
        nullable=False,
    )

    file_name = Column(
        String(255),
        nullable=False,
    )

    mime_type = Column(
        String(100),
        nullable=True,
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    invoice = relationship(
        "AccountingInvoice",
        back_populates="attachments",
    )

    expense = relationship(
        "AccountingExpense",
        back_populates="attachments",
    )
