from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==========================================================
# CHECKOUT
# ==========================================================

class CreatePaddleCheckoutResponse(BaseModel):
    """
    Respuesta del endpoint POST /api/paddle/checkout.

    Contiene todo lo necesario para inicializar
    Paddle.js Inline Checkout en el frontend.
    """

    # ID del precio en Paddle (pri_xxx)
    price_id: str

    # Token público para Paddle.js (diferente a la API Key)
    client_token: str

    # "sandbox" | "production"
    environment: str = "sandbox"

    # Información del plan para mostrar en el modal
    plan_name: str = ""
    amount: float = 0.0
    currency: str = "USD"

    # Customer de Paddle (opcional, pre-rellena el checkout)
    paddle_customer_id: Optional[str] = None


# ==========================================================
# SUSCRIPCIÓN
# ==========================================================

class DoctorPaddleSubscriptionResponse(BaseModel):
    id: int
    doctor_id: int
    subscription_plan_id: int

    status: str

    provider: Optional[str] = None
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None

    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None

    cancel_at_period_end: bool
    cancelled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================================
# PAGO
# ==========================================================

class DoctorPaddlePaymentResponse(BaseModel):
    id: int

    doctor_id: int
    doctor_subscription_id: int

    paddle_transaction_id: Optional[str] = None
    paddle_subscription_id: Optional[str] = None

    amount: float
    currency: str
    status: str

    paid_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================================
# CANCELAR SUSCRIPCIÓN
# ==========================================================

class CancelPaddleSubscriptionRequest(BaseModel):
    immediately: bool = Field(
        default=False,
        description=(
            "Si es true, cancela la suscripción de inmediato. "
            "Si es false (default), cancela al final del período."
        ),
    )


class CancelPaddleSubscriptionResponse(BaseModel):
    message: str
    status: str