
# app/services/accounting_service.py

import asyncio
import os
from decimal import Decimal
from uuid import UUID

import cloudinary
import cloudinary.uploader

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.accounting_transaction import AccountingTransaction
from app.models.accounting_expense import AccountingExpense
from app.models.accounting_attachment import AccountingAttachment
from app.schemas.accounting import AccountingMovementCreate


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )


class AccountingService:

    @staticmethod
    def create_movement(
        db: Session,
        doctor_id: int,
        data: AccountingMovementCreate,
    ):
        """
        Crea el movimiento contable y, si es un gasto,
        también crea su registro de gasto asociado.

        doctor_id debe proceder del usuario autenticado.
        """

        if data.type == "expense" and not data.category:
            raise HTTPException(
                status_code=422,
                detail="La categoría es obligatoria para un gasto.",
            )

        if data.type == "expense" and not data.expense_date:
            raise HTTPException(
                status_code=422,
                detail="La fecha del gasto es obligatoria.",
            )

        expense = None

        try:
            # Crear el detalle del gasto cuando corresponda.
            if data.type == "expense":
                expense = AccountingExpense(
                    doctor_id=doctor_id,
                    category=data.category,
                    description=data.description,
                    amount=data.amount,
                    currency=data.currency,
                    supplier_name=data.supplier_name,
                    expense_date=data.expense_date,
                    payment_method=data.payment_method,
                    status=(
                        "paid"
                        if data.status == "completed"
                        else "pending"
                    ),
                    notes=data.notes,
                )

                db.add(expense)
                db.flush()

            # Registrar el movimiento contable.
            movement = AccountingTransaction(
                doctor_id=doctor_id,
                type=data.type,
                source=data.source,
                amount=data.amount,
                currency=data.currency,
                status=data.status,
                expense_id=expense.id if expense else None,
                external_reference=data.external_reference or data.description,
                occurred_at=data.occurred_at,
            )

            db.add(movement)
            db.commit()

            db.refresh(movement)

            if expense:
                db.refresh(expense)

            return movement, expense

        except Exception:
            db.rollback()
            raise

    @staticmethod
    async def upload_attachment(
        db: Session,
        doctor_id: int,
        movement_id: UUID,
        file: UploadFile,
    ) -> AccountingAttachment:
        """
        Sube el archivo a Cloudinary y registra sus metadatos.
        Solo permite adjuntar soportes a movimientos del médico.
        """

        movement = (
            db.query(AccountingTransaction)
            .filter(
                AccountingTransaction.id == movement_id,
                AccountingTransaction.doctor_id == doctor_id,
            )
            .first()
        )

        if movement is None:
            raise HTTPException(
                status_code=404,
                detail="Movimiento contable no encontrado.",
            )

        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Solo se permiten PDF, JPG, PNG y WEBP.",
            )

        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío.",
            )

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="El archivo supera el límite de 10 MB.",
            )

        configure_cloudinary()

        try:
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                content,
                resource_type="auto",
                folder=f"medical_ai/accounting/{doctor_id}",
                use_filename=False,
                unique_filename=True,
            )

            attachment = AccountingAttachment(
                doctor_id=doctor_id,
                expense_id=movement.expense_id,
                invoice_id=movement.invoice_id,
                file_url=result["secure_url"],
                file_name=file.filename or "documento",
                mime_type=file.content_type,
            )

            db.add(attachment)
            db.commit()
            db.refresh(attachment)

            return attachment

        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=502,
                detail="No fue posible subir o registrar el archivo.",
            ) from exc

    @staticmethod
    def list_movements(
        db: Session,
        doctor_id: int,
        movement_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        query = db.query(AccountingTransaction).filter(
            AccountingTransaction.doctor_id == doctor_id
        )

        if movement_type:
            query = query.filter(
                AccountingTransaction.type == movement_type
            )

        return (
            query.order_by(AccountingTransaction.occurred_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
