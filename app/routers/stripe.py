from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.doctor import Doctor
from app.models.doctor_subscription import DoctorSubscription
from app.models.payment_doctor import PaymentDoctor
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.services.stripe_service import stripe_service

router = APIRouter(
    prefix="/api/stripe",
    tags=["Stripe Payments"],
)

# ==========================================================
# HELPER: Obtener doctor activo por user_id
# ==========================================================
def _get_doctor_by_user_id(user_id: int, db: Session) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado para este usuario.",
        )
    return doctor

# ==========================================================
# CREAR CHECKOUT SESSION PARA SUSCRIPCIÓN
# ==========================================================
@router.post("/create-checkout-session")
async def create_checkout_session(
    user_id: int,
    plan_id: int,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Inicia una sesión de Stripe Checkout en modo 'subscription'
    para que el médico pague su membresía mensual.

    - user_id: ID del usuario (doctor)
    - plan_id: ID del plan de suscripción
    - success_url: URL de redirección tras pago exitoso (opcional, se genera desde FRONTEND_URL)
    - cancel_url: URL de redirección si el usuario cancela (opcional, se genera desde FRONTEND_URL)
    """
    doctor = _get_doctor_by_user_id(user_id, db)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active == True
    ).first()

    if not plan or plan.is_free:
        raise HTTPException(status_code=400, detail="Plan no válido o gratuito.")

    price_id = (
        getattr(plan, 'stripe_price_id', None)
        or getattr(plan, 'paddle_price_id', None)
        or settings.STRIPE_DOCTOR_PRICE_ID
    )
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail="No hay un Stripe Price ID configurado para este plan.",
        )

    # 1. Buscar o crear Customer en Stripe por email
    try:
        existing = stripe_service.list_customers_by_email(user.email)
        if existing:
            stripe_customer_id = existing[0].id
        else:
            customer = stripe_service.create_customer(
                email=user.email,
                name=f"{doctor.first_name} {doctor.last_name}",
                metadata={"user_id": str(user_id), "doctor_id": str(doctor.id)},
            )
            stripe_customer_id = customer.id
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al crear customer en Stripe: {str(e)}",
        )

    # 2. Crear un registro de suscripción en estado 'pending'
    subscription = DoctorSubscription(
        doctor_id=doctor.id,
        subscription_plan_id=plan.id,
        status="pending",
        provider="stripe",
        provider_customer_id=stripe_customer_id,
        cancel_at_period_end=False,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # 3. Resolver URLs de redirección
    frontend_base = settings.FRONTEND_URL.rstrip("/")
    resolved_success_url = (
        success_url
        or f"{frontend_base}/doctor/upgrade?stripe=success&session_id={{CHECKOUT_SESSION_ID}}"
    )
    resolved_cancel_url = (
        cancel_url
        or f"{frontend_base}/doctor/upgrade?stripe=cancel"
    )

    # 4. Crear la sesión de Checkout en Stripe
    try:
        session = stripe_service.create_checkout_session(
            customer_id=stripe_customer_id,
            price_id=price_id,
            success_url=resolved_success_url,
            cancel_url=resolved_cancel_url,
            doctor_id=doctor.id,
            doctor_subscription_id=subscription.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al crear sesión en Stripe: {str(e)}",
        )

    return {"checkout_url": session.url, "session_id": session.id}


# ==========================================================
# WEBHOOK DE STRIPE
# ==========================================================
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Recibe los eventos de Stripe (suscripciones, pagos exitosos, etc.)
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe_service.construct_webhook_event(payload, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {str(e)}")

    event_type = event["type"]
    data_object = event["data"]["object"]

    # ----------------------------------------------------------
    # checkout.session.completed (Pago inicial y suscripción creada)
    # ----------------------------------------------------------
    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata", {})
        doctor_id = metadata.get("doctor_id")
        doctor_subscription_id = metadata.get("doctor_subscription_id")
        stripe_subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        amount_total = data_object.get("amount_total", 0) / 100
        currency = data_object.get("currency", "gbp").upper()
        payment_intent_id = data_object.get("payment_intent")

        if doctor_subscription_id:
            subscription = db.query(DoctorSubscription).filter(
                DoctorSubscription.id == int(doctor_subscription_id)
            ).first()

            if subscription:
                subscription.status = "active"
                subscription.provider_subscription_id = stripe_subscription_id
                subscription.provider_customer_id = customer_id
                subscription.current_period_start = datetime.utcnow()
                subscription.updated_at = datetime.utcnow()

                # Registrar el pago en PaymentDoctor
                payment = PaymentDoctor(
                    doctor_id=int(doctor_id),
                    doctor_subscription_id=subscription.id,
                    paddle_transaction_id=payment_intent_id,  # campo reutilizado para Stripe
                    amount=amount_total,
                    currency=currency,
                    status="paid",
                    paid_at=datetime.utcnow(),
                )
                db.add(payment)
                db.commit()

    # ----------------------------------------------------------
    # invoice.payment_succeeded (Renovación de suscripción mensual)
    # ----------------------------------------------------------
    elif event_type == "invoice.payment_succeeded":
        stripe_subscription_id = data_object.get("subscription")
        if stripe_subscription_id:
            subscription = db.query(DoctorSubscription).filter(
                DoctorSubscription.provider_subscription_id == stripe_subscription_id
            ).first()

            if subscription:
                subscription.status = "active"
                subscription.updated_at = datetime.utcnow()
                db.commit()

    # ----------------------------------------------------------
    # customer.subscription.deleted (Suscripción cancelada definitivamente)
    # ----------------------------------------------------------
    elif event_type == "customer.subscription.deleted":
        stripe_subscription_id = data_object.get("id")
        if stripe_subscription_id:
            subscription = db.query(DoctorSubscription).filter(
                DoctorSubscription.provider_subscription_id == stripe_subscription_id
            ).first()

            if subscription:
                subscription.status = "canceled"
                subscription.ended_at = datetime.utcnow()
                db.commit()

    return {"status": "success"}