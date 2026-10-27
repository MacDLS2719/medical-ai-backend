
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AccountingTransaction(Base):
    __tablename__ = "accounting_transactions"

    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense', 'commission', 'refund', 'adjustment')",
            name="ck_accounting_transactions_type",
        ),
        CheckConstraint(
            "source IN ('stripe', 'cash', 'bank_transfer', 'external', 'other')",
            name="ck_accounting_transactions_source",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')",
            name="ck_accounting_transactions_status",
        ),
        CheckConstraint(
            "amount >= 0",
            name="ck_accounting_transactions_amount",
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

    type = Column(
        String(30),
        nullable=False,
    )

    source = Column(
        String(30),
        nullable=False,
    )

    amount = Column(
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
        default="pending",
        server_default="pending",
        index=True,
    )

    appointment_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounting_invoices.id", ondelete="SET NULL"),
        nullable=True,
    )

    expense_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounting_expenses.id", ondelete="SET NULL"),
        nullable=True,
    )

    external_reference = Column(
        String(255),
        nullable=True,
        index=True,
    )

    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
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

    invoice = relationship(
        "AccountingInvoice",
        back_populates="transactions",
    )

    expense = relationship(
        "AccountingExpense",
        back_populates="transactions",
        lazy="joined",
    )

    @property
    def description(self) -> str | None:
        if self.expense and self.expense.description:
            return self.expense.description
        return self.external_reference or ("Ingreso por consulta" if self.type == "income" else "Movimiento contable")

    @property
    def category(self) -> str:
        if self.expense and self.expense.category:
            return self.expense.category
        return "Consultas" if self.type == "income" else "General"

    @property
    def supplier_name(self) -> str | None:
        if self.expense:
            return self.expense.supplier_name
        return None
