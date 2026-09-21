from datetime import datetime

from pydantic import BaseModel, Field


# ==========================================================
# CREAR CHECKOUT
# ==========================================================

class CreateCheckoutSessionRequest(BaseModel):
    """
    Información necesaria para iniciar el proceso
    de suscripción del médico.
    """

    doctor_subscription_id: int = Field(
        ...,
        description="ID de la suscripción del médico",
    )


class CreateCheckoutSessionResponse(BaseModel):
    """
    Respuesta del backend después de crear
    la sesión de Stripe Checkout.
    """

    checkout_url: str
    session_id: str


# ==========================================================
# SUSCRIPCIÓN
# ==========================================================

class DoctorSubscriptionResponse(BaseModel):
    id: int
    doctor_id: int
    subscription_plan_id: int

    status: str

    provider: str | None = None
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None

    current_period_start: datetime | None = None
    current_period_end: datetime | None = None

    cancel_at_period_end: bool
    cancelled_at: datetime | None = None
    ended_at: datetime | None = None

    class Config:
        from_attributes = True


# ==========================================================
# PAGO
# ==========================================================

class DoctorPaymentResponse(BaseModel):
    id: int

    doctor_id: int
    doctor_subscription_id: int

    stripe_payment_intent_id: str | None = None
    stripe_invoice_id: str | None = None
    stripe_charge_id: str | None = None

    amount: float
    currency: str
    status: str

    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================================
# CANCELAR SUSCRIPCIÓN
# ==========================================================

class CancelSubscriptionRequest(BaseModel):
    immediately: bool = False


class CancelSubscriptionResponse(BaseModel):
    message: str
    cancel_at_period_end: bool
    status: str