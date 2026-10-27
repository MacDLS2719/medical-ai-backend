
"""Create medical accounting tables.

Revision ID: ac1446eb6024
Revises: 06dd7454551f
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ac1446eb6024"
down_revision: Union[str, Sequence[str], None] = "06dd7454551f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Facturas
    op.create_table(
        "accounting_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "doctor_id",
            "invoice_number",
            name="uq_accounting_invoices_doctor_number",
        ),
        sa.CheckConstraint(
            "subtotal >= 0 AND tax_amount >= 0 AND total_amount >= 0",
            name="ck_accounting_invoices_amounts",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'paid', 'void', 'refunded')",
            name="ck_accounting_invoices_status",
        ),
    )

    # 2. Gastos
    op.create_table(
        "accounting_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount >= 0", name="ck_accounting_expenses_amount"),
        sa.CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled')",
            name="ck_accounting_expenses_status",
        ),
    )

    # 3. Movimientos contables
    op.create_table(
        "accounting_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounting_invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "expense_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounting_expenses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('income', 'expense', 'commission', 'refund', 'adjustment')",
            name="ck_accounting_transactions_type",
        ),
        sa.CheckConstraint(
            "source IN ('stripe', 'cash', 'bank_transfer', 'external', 'other')",
            name="ck_accounting_transactions_source",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')",
            name="ck_accounting_transactions_status",
        ),
        sa.CheckConstraint("amount >= 0", name="ck_accounting_transactions_amount"),
    )

    # 4. Archivos adjuntos
    op.create_table(
        "accounting_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounting_invoices.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "expense_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounting_expenses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(invoice_id IS NOT NULL AND expense_id IS NULL) OR "
            "(invoice_id IS NULL AND expense_id IS NOT NULL)",
            name="ck_accounting_attachments_one_parent",
        ),
    )

    # Índices
    for table, column in [
        ("accounting_invoices", "doctor_id"),
        ("accounting_invoices", "patient_id"),
        ("accounting_invoices", "appointment_id"),
        ("accounting_expenses", "doctor_id"),
        ("accounting_expenses", "expense_date"),
        ("accounting_transactions", "doctor_id"),
        ("accounting_transactions", "appointment_id"),
        ("accounting_transactions", "status"),
        ("accounting_transactions", "occurred_at"),
        ("accounting_transactions", "external_reference"),
        ("accounting_attachments", "doctor_id"),
    ]:
        op.create_index(
            f"ix_{table}_{column}",
            table,
            [column],
        )


def downgrade() -> None:
    # Eliminar índices y tablas en orden inverso de dependencias.
    for table, column in [
        ("accounting_attachments", "doctor_id"),
        ("accounting_transactions", "external_reference"),
        ("accounting_transactions", "occurred_at"),
        ("accounting_transactions", "status"),
        ("accounting_transactions", "appointment_id"),
        ("accounting_transactions", "doctor_id"),
        ("accounting_expenses", "expense_date"),
        ("accounting_expenses", "doctor_id"),
        ("accounting_invoices", "appointment_id"),
        ("accounting_invoices", "patient_id"),
        ("accounting_invoices", "doctor_id"),
    ]:
        op.drop_index(f"ix_{table}_{column}", table_name=table)

    op.drop_table("accounting_attachments")
    op.drop_table("accounting_transactions")
    op.drop_table("accounting_expenses")
    op.drop_table("accounting_invoices")
