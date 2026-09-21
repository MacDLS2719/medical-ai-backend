from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.payment import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
)
from app.services.stripe_service import stripe_service


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


# ==========================================================
# CREAR CHECKOUT SESSION
# ==========================================================

@router.post(
    "/create-checkout-session",
    response_model=CreateCheckoutSessionResponse,
)
def create_checkout_session(
    data: CreateCheckoutSessionRequest,
    db: Session = Depends(get_db),
):
    """
    Crea una sesión de Stripe Checkout.

    IMPORTANTE:
    La lógica completa de validación del doctor,
    suscripción y plan la agregaremos aquí antes
    de permitir crear el Checkout.
    """

    # ------------------------------------------------------
    # TEMPORAL
    # ------------------------------------------------------
    #
    # En el siguiente paso vamos a consultar:
    #
    # DoctorSubscription
    # SubscriptionPlan
    # Doctor
    #
    # y obtendremos:
    #
    # - doctor_id
    # - customer_id
    # - Stripe Price ID
    #
    # ------------------------------------------------------

    raise HTTPException(
        status_code=501,
        detail=(
            "La creación del Checkout está preparada, "
            "pero falta conectar DoctorSubscription "
            "y SubscriptionPlan."
        ),
    )