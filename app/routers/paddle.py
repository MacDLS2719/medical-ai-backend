from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.doctor import Doctor
from app.models.doctor_subscription import DoctorSubscription
from app.models.payment_doctor import PaymentDoctor
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.schemas.paddle import (
    CancelPaddleSubscriptionRequest,
    CancelPaddleSubscriptionResponse,
    CreatePaddleCheckoutResponse,
    DoctorPaddleSubscriptionResponse,
)
from app.services.paddle_service import paddle_service


router = APIRouter(
    prefix="/api/paddle",
    tags=["Paddle Payments"],
)


# ==========================================================
# HELPER: Obtener doctor activo por user_id
# ==========================================================

def _get_doctor_by_user_id(
    user_id: int,
    db: Session,
) -> Doctor:
    """
    Obtiene el doctor a partir del user_id.
    Lanza 404 si no existe.
    """
    doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == user_id)
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor no encontrado para este usuario.",
        )
    return doctor


# ==========================================================
# CREAR CHECKOUT
# ==========================================================

@router.post(
    "/checkout",
    response_model=CreatePaddleCheckoutResponse,
)
async def create_checkout(
    user_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
):
    """
    Prepara la información necesaria para abrir Paddle Checkout
    desde el frontend (Paddle.js Inline Checkout).

    Recibe el user_id del médico y el plan_id seleccionado.
    Retorna:
      - price_id: ID del precio en Paddle (pri_xxx)
      - client_token: token público para inicializar Paddle.js
      - environment: 'sandbox' | 'production'
      - plan_name: nombre del plan para mostrar en el modal
      - amount: precio del plan
      - currency: moneda
    """

    # 1. Obtener el doctor
    doctor = _get_doctor_by_user_id(user_id, db)

    # 2. Obtener el plan de suscripción
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.is_active == True,
        )
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan de suscripción no encontrado.",
        )

    if plan.is_free:
        raise HTTPException(
            status_code=400,
            detail="El plan gratuito no requiere pago.",
        )

    # 3. Resolver el price_id de Paddle
    # Primero usamos el paddle_price_id del plan (si está configurado),
    # luego el PADDLE_DOCTOR_PRICE_ID global del .env como fallback.
    price_id = plan.paddle_price_id or settings.PADDLE_DOCTOR_PRICE_ID

    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=(
                "No hay un Paddle Price ID configurado para este plan. "
                "Configura 'paddle_price_id' en el plan o "
                "'PADDLE_DOCTOR_PRICE_ID' en el entorno."
            ),
        )

    # 4. Obtener o crear el customer de Paddle para el doctor
    user = db.query(User).filter(User.id == user_id).first()
    customer_email = user.email if user else None

    paddle_customer_id = None
    if customer_email and settings.PADDLE_API_KEY:
        try:
            customer = await paddle_service.get_or_create_customer(
                email=customer_email,
                name=(
                    f"{doctor.first_name} {doctor.last_name}"
                    if doctor.first_name and doctor.last_name
                    else None
                ),
            )
            paddle_customer_id = customer.get("id")
        except Exception:
            # Si falla la creación del customer, continuamos sin él
            # El médico podrá ingresar sus datos en el checkout de Paddle
            paddle_customer_id = None

    # 5. Retornar datos para inicializar el checkout
    return CreatePaddleCheckoutResponse(
        price_id=price_id,
        client_token=paddle_service.get_client_token(),
        environment=paddle_service.get_environment(),
        plan_name=plan.name,
        amount=float(plan.price),
        currency=plan.currency,
        paddle_customer_id=paddle_customer_id,
    )


# ==========================================================
# WEBHOOK
# ==========================================================

@router.post("/webhook")
async def paddle_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Recibe y procesa eventos enviados por Paddle vía webhook.

    Eventos manejados:
      - transaction.completed    → activa suscripción + registra pago
      - subscription.created     → registra provider_subscription_id
      - subscription.updated     → actualiza período de suscripción
      - subscription.canceled    → marca suscripción como cancelada
      - transaction.payment_failed → marca suscripción como past_due
    """

    payload = await request.body()

    signature = request.headers.get("Paddle-Signature", "")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Falta la cabecera Paddle-Signature.",
        )

    # Verificar firma (solo si el webhook secret está configurado)
    if settings.PADDLE_WEBHOOK_SECRET:
        is_valid = paddle_service.verify_webhook_signature(
            payload=payload,
            signature=signature,
        )

        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail="Firma de Paddle inválida o expirada.",
            )

    event = await request.json()
    event_type = event.get("event_type", "")
    event_data = event.get("data", {})

    # ----------------------------------------------------------
    # transaction.completed
    # ----------------------------------------------------------
    if event_type == "transaction.completed":
        await _handle_transaction_completed(event_data, db)

    # ----------------------------------------------------------
    # subscription.created
    # ----------------------------------------------------------
    elif event_type == "subscription.created":
        _handle_subscription_created(event_data, db)

    # ----------------------------------------------------------
    # subscription.updated
    # ----------------------------------------------------------
    elif event_type == "subscription.updated":
        _handle_subscription_updated(event_data, db)

    # ----------------------------------------------------------
    # subscription.canceled
    # ----------------------------------------------------------
    elif event_type in ("subscription.canceled", "subscription.cancelled"):
        _handle_subscription_canceled(event_data, db)

    # ----------------------------------------------------------
    # transaction.payment_failed
    # ----------------------------------------------------------
    elif event_type == "transaction.payment_failed":
        _handle_payment_failed(event_data, db)

    return {
        "received": True,
        "event_type": event_type,
    }


# ==========================================================
# HANDLERS DE WEBHOOK
# ==========================================================

async def _handle_transaction_completed(
    data: dict,
    db: Session,
) -> None:
    """
    Procesa una transacción completada:
      1. Identifica el doctor por el customer email o custom_data
      2. Activa o crea su DoctorSubscription
      3. Registra el pago en PaymentDoctor
    """

    transaction_id = data.get("id")
    subscription_id = data.get("subscription_id")
    customer_id = data.get("customer_id")

    # Obtener info del plan desde los items de la transacción
    items = data.get("items", [])
    price_id = None
    if items:
        price_id = items[0].get("price", {}).get("id")

    # Datos del pago
    details = data.get("details", {})
    totals = details.get("totals", {})
    amount_raw = totals.get("grand_total", "0")
    currency = data.get("currency_code", "USD")

    try:
        amount = float(amount_raw) / 100  # Paddle retorna en centavos
    except (TypeError, ValueError):
        amount = 0.0

    # Identificar el plan por price_id
    plan = None
    if price_id:
        plan = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.paddle_price_id == price_id)
            .first()
        )
        if not plan and settings.PADDLE_DOCTOR_PRICE_ID == price_id:
            # Buscar el plan profesional como fallback
            plan = (
                db.query(SubscriptionPlan)
                .filter(
                    SubscriptionPlan.name.ilike("%professional%")
                    | SubscriptionPlan.name.ilike("%profesional%")
                    | SubscriptionPlan.slug.ilike("%professional%")
                )
                .first()
            )

    if not plan:
        # No se puede identificar el plan, registrar y salir
        print(
            f"[PaddleWebhook] transaction.completed sin plan identificado. "
            f"price_id={price_id}, transaction_id={transaction_id}"
        )
        return

    # Identificar al doctor por custom_data (si el frontend lo envía)
    custom_data = data.get("custom_data") or {}
    user_id = custom_data.get("user_id")

    doctor = None
    if user_id:
        doctor = (
            db.query(Doctor)
            .filter(Doctor.user_id == int(user_id))
            .first()
        )

    if not doctor:
        # Intentar por email del customer
        customer_email = (
            data.get("customer", {}).get("email")
            or data.get("billing_details", {}).get("email")
        )
        if customer_email:
            user = (
                db.query(User)
                .filter(User.email == customer_email)
                .first()
            )
            if user:
                doctor = (
                    db.query(Doctor)
                    .filter(Doctor.user_id == user.id)
                    .first()
                )

    if not doctor:
        print(
            f"[PaddleWebhook] transaction.completed: doctor no identificado. "
            f"transaction_id={transaction_id}"
        )
        return

    # Buscar suscripción activa/pendiente del doctor para este plan
    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.doctor_id == doctor.id,
            DoctorSubscription.subscription_plan_id == plan.id,
        )
        .order_by(DoctorSubscription.created_at.desc())
        .first()
    )

    now = datetime.utcnow()

    if subscription:
        # Actualizar la suscripción existente
        subscription.status = "active"
        subscription.provider = "paddle"
        subscription.provider_customer_id = customer_id
        if subscription_id:
            subscription.provider_subscription_id = subscription_id
        subscription.current_period_start = now
        subscription.updated_at = now
    else:
        # Crear nueva suscripción
        subscription = DoctorSubscription(
            doctor_id=doctor.id,
            subscription_plan_id=plan.id,
            status="active",
            provider="paddle",
            provider_customer_id=customer_id,
            provider_subscription_id=subscription_id,
            current_period_start=now,
            cancel_at_period_end=False,
        )
        db.add(subscription)
        db.flush()  # Para obtener el ID

    # Evitar duplicados de pago por transaction_id
    existing_payment = (
        db.query(PaymentDoctor)
        .filter(PaymentDoctor.paddle_transaction_id == transaction_id)
        .first()
    )

    if not existing_payment and transaction_id:
        payment = PaymentDoctor(
            doctor_id=doctor.id,
            doctor_subscription_id=subscription.id,
            paddle_transaction_id=transaction_id,
            paddle_subscription_id=subscription_id,
            amount=amount,
            currency=currency,
            status="paid",
            paid_at=now,
        )
        db.add(payment)

    db.commit()

    print(
        f"[PaddleWebhook] transaction.completed procesado: "
        f"doctor_id={doctor.id}, plan={plan.name}, "
        f"transaction_id={transaction_id}"
    )


def _handle_subscription_created(data: dict, db: Session) -> None:
    """
    Registra el provider_subscription_id cuando Paddle
    crea la suscripción.
    """
    subscription_id = data.get("id")
    customer_id = data.get("customer_id")

    if not subscription_id:
        return

    # Buscar por provider_customer_id o subscription reciente sin sub_id
    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.provider_customer_id == customer_id,
            DoctorSubscription.provider_subscription_id.is_(None),
        )
        .order_by(DoctorSubscription.created_at.desc())
        .first()
    )

    if subscription:
        subscription.provider_subscription_id = subscription_id
        subscription.provider = "paddle"

        # Actualizar período
        current_period = data.get("current_billing_period", {})
        if current_period.get("starts_at"):
            try:
                subscription.current_period_start = datetime.fromisoformat(
                    current_period["starts_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        if current_period.get("ends_at"):
            try:
                subscription.current_period_end = datetime.fromisoformat(
                    current_period["ends_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        db.commit()


def _handle_subscription_updated(data: dict, db: Session) -> None:
    """
    Actualiza el período y estado cuando Paddle modifica
    una suscripción.
    """
    subscription_id = data.get("id")
    if not subscription_id:
        return

    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.provider_subscription_id == subscription_id
        )
        .first()
    )

    if not subscription:
        return

    # Estado de Paddle → estado interno
    paddle_status = data.get("status", "")
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "paused": "paused",
        "canceled": "canceled",
        "trialing": "trialing",
    }
    subscription.status = status_map.get(paddle_status, paddle_status)

    # Actualizar período
    current_period = data.get("current_billing_period", {})
    if current_period.get("starts_at"):
        try:
            subscription.current_period_start = datetime.fromisoformat(
                current_period["starts_at"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass
    if current_period.get("ends_at"):
        try:
            subscription.current_period_end = datetime.fromisoformat(
                current_period["ends_at"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    # Cancelación al final del período
    scheduled_change = data.get("scheduled_change")
    if scheduled_change and scheduled_change.get("action") == "cancel":
        subscription.cancel_at_period_end = True

    db.commit()


def _handle_subscription_canceled(data: dict, db: Session) -> None:
    """
    Marca la suscripción como cancelada.
    """
    subscription_id = data.get("id")
    if not subscription_id:
        return

    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.provider_subscription_id == subscription_id
        )
        .first()
    )

    if not subscription:
        return

    now = datetime.utcnow()
    subscription.status = "canceled"
    subscription.cancelled_at = now

    canceled_at_str = data.get("canceled_at")
    if canceled_at_str:
        try:
            subscription.ended_at = datetime.fromisoformat(
                canceled_at_str.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            subscription.ended_at = now

    db.commit()


def _handle_payment_failed(data: dict, db: Session) -> None:
    """
    Marca la suscripción como past_due cuando un pago falla.
    """
    subscription_id = data.get("subscription_id")
    if not subscription_id:
        return

    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.provider_subscription_id == subscription_id
        )
        .first()
    )

    if subscription:
        subscription.status = "past_due"
        db.commit()


# ==========================================================
# OBTENER SUSCRIPCIÓN DEL DOCTOR
# ==========================================================

@router.get(
    "/subscription/{user_id}",
    response_model=DoctorPaddleSubscriptionResponse,
)
def get_doctor_subscription(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna la suscripción activa del doctor.
    """
    doctor = _get_doctor_by_user_id(user_id, db)

    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.doctor_id == doctor.id,
            DoctorSubscription.status.in_(["active", "trialing", "past_due"]),
        )
        .order_by(DoctorSubscription.created_at.desc())
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="El doctor no tiene una suscripción activa.",
        )

    return subscription


# ==========================================================
# CANCELAR SUSCRIPCIÓN
# ==========================================================

@router.post(
    "/subscription/{user_id}/cancel",
    response_model=CancelPaddleSubscriptionResponse,
)
async def cancel_doctor_subscription(
    user_id: int,
    data: CancelPaddleSubscriptionRequest,
    db: Session = Depends(get_db),
):
    """
    Cancela la suscripción activa del doctor en Paddle.
    """
    doctor = _get_doctor_by_user_id(user_id, db)

    subscription = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.doctor_id == doctor.id,
            DoctorSubscription.status.in_(["active", "trialing"]),
            DoctorSubscription.provider == "paddle",
        )
        .order_by(DoctorSubscription.created_at.desc())
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una suscripción activa de Paddle.",
        )

    if not subscription.provider_subscription_id:
        raise HTTPException(
            status_code=400,
            detail="Esta suscripción no tiene un ID de Paddle asociado.",
        )

    try:
        await paddle_service.cancel_subscription(
            subscription.provider_subscription_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al cancelar en Paddle: {str(e)}",
        )

    now = datetime.utcnow()

    if data.immediately:
        subscription.status = "canceled"
        subscription.cancelled_at = now
        subscription.ended_at = now
    else:
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = now

    db.commit()

    return CancelPaddleSubscriptionResponse(
        message=(
            "Suscripción cancelada inmediatamente."
            if data.immediately
            else "La suscripción se cancelará al final del período actual."
        ),
        status=subscription.status,
    )