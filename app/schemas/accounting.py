
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


TransactionType = Literal[
    "income",
    "expense",
    "commission",
    "refund",
    "adjustment",
]

TransactionSource = Literal[
    "cash",
    "bank_transfer",
    "external",
    "other",
]

TransactionStatus = Literal[
    "pending",
    "completed",
    "cancelled",
]

ExpenseStatus = Literal[
    "pending",
    "paid",
    "cancelled",
]


class AccountingMovementCreate(BaseModel):
    type: TransactionType
    source: TransactionSource = "external"
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="COP", min_length=3, max_length=3)
    description: str = Field(min_length=2, max_length=500)
    occurred_at: datetime
    status: TransactionStatus = "completed"
    external_reference: str | None = Field(default=None, max_length=255)

    # Campos específicos de los gastos.
    category: str | None = Field(default=None, max_length=100)
    supplier_name: str | None = Field(default=None, max_length=255)
    expense_date: date | None = None
    payment_method: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("type")
    @classmethod
    def validate_expense_category(
        cls,
        value: TransactionType,
        info,
    ) -> TransactionType:
        return value


class AccountingAttachmentRead(BaseModel):
    id: UUID
    file_url: str
    file_name: str
    mime_type: str | None = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountingMovementRead(BaseModel):
    id: UUID
    type: str
    source: str
    amount: Decimal
    currency: str
    status: str
    external_reference: str | None = None
    description: str | None = None
    category: str | None = None
    supplier_name: str | None = None
    occurred_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountingExpenseRead(BaseModel):
    id: UUID
    category: str
    description: str
    amount: Decimal
    currency: str
    supplier_name: str | None = None
    expense_date: date
    payment_method: str | None = None
    status: str
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AccountingMovementDetail(BaseModel):
    movement: AccountingMovementRead
    expense: AccountingExpenseRead | None = None
    attachments: list[AccountingAttachmentRead] = []
