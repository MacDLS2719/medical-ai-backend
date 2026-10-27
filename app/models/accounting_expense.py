
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AccountingExpense(Base):
    __tablename__ = "accounting_expenses"

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_accounting_expenses_amount",
        ),
        CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled')",
            name="ck_accounting_expenses_status",
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

    category = Column(
        String(100),
        nullable=False,
    )

    description = Column(
        Text,
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

    supplier_name = Column(
        String(255),
        nullable=True,
    )

    expense_date = Column(
        Date,
        nullable=False,
        index=True,
    )

    payment_method = Column(
        String(50),
        nullable=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    notes = Column(
        Text,
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
        back_populates="expense",
    )

    attachments = relationship(
        "AccountingAttachment",
        back_populates="expense",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
