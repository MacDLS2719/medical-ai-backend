import stripe

from typing import Any

from app.core.config import settings


class StripeService:
    """
    Servicio centralizado para la comunicación con Stripe.

    Este servicio NO maneja datos de tarjeta directamente.
    Stripe Checkout se encarga de la información sensible del pago.
    """

    def __init__(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError(
                "STRIPE_SECRET_KEY no está configurada."
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

    # ==========================================================
    # CUSTOMER
    # ==========================================================

    def create_customer(
        self,
        *,
        email: str,
        name: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> stripe.Customer:
        """
        Crea un Customer en Stripe.
        """

        customer_data: dict[str, Any] = {
            "email": email,
        }

        if name:
            customer_data["name"] = name

        if metadata:
            customer_data["metadata"] = metadata

        return stripe.Customer.create(
            **customer_data
        )

    # ==========================================================
    # OBTENER CUSTOMER
    # ==========================================================

    def retrieve_customer(
        self,
        customer_id: str,
    ) -> stripe.Customer:
        """
        Obtiene un Customer existente de Stripe.
        """

        return stripe.Customer.retrieve(
            customer_id
        )

    # ==========================================================
    # CHECKOUT SESSION
    # ==========================================================

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        doctor_id: int,
        doctor_subscription_id: int,
    ) -> stripe.checkout.Session:
        """
        Crea una sesión de Stripe Checkout para una suscripción.

        Stripe será quien muestre y procese el formulario de pago.
        """

        session = stripe.checkout.Session.create(
            customer=customer_id,

            mode="subscription",

            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],

            success_url=success_url,
            cancel_url=cancel_url,

            metadata={
                "doctor_id": str(doctor_id),
                "doctor_subscription_id": str(
                    doctor_subscription_id
                ),
            },

            subscription_data={
                "metadata": {
                    "doctor_id": str(doctor_id),
                    "doctor_subscription_id": str(
                        doctor_subscription_id
                    ),
                }
            },
        )

        return session

    # ==========================================================
    # OBTENER CHECKOUT SESSION
    # ==========================================================

    def retrieve_checkout_session(
        self,
        session_id: str,
    ) -> stripe.checkout.Session:
        """
        Obtiene una sesión de Checkout existente.
        """

        return stripe.checkout.Session.retrieve(
            session_id
        )

    # ==========================================================
    # OBTENER SUSCRIPCIÓN DE STRIPE
    # ==========================================================

    def retrieve_subscription(
        self,
        subscription_id: str,
    ) -> stripe.Subscription:
        """
        Obtiene una suscripción directamente desde Stripe.
        """

        return stripe.Subscription.retrieve(
            subscription_id
        )

    # ==========================================================
    # CANCELAR SUSCRIPCIÓN AL FINAL DEL PERÍODO
    # ==========================================================

    def cancel_subscription_at_period_end(
        self,
        subscription_id: str,
    ) -> stripe.Subscription:
        """
        Marca la suscripción para cancelarse al finalizar
        el período actual.

        El usuario mantiene acceso hasta current_period_end.
        """

        return stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )

    # ==========================================================
    # CANCELAR INMEDIATAMENTE
    # ==========================================================

    def cancel_subscription(
        self,
        subscription_id: str,
    ) -> stripe.Subscription:
        """
        Cancela inmediatamente una suscripción en Stripe.
        """

        return stripe.Subscription.cancel(
            subscription_id
        )

    # ==========================================================
    # CREAR PORTAL DE FACTURACIÓN
    # ==========================================================

    def create_billing_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        """
        Crea una sesión del Customer Portal de Stripe.

        El médico podrá gestionar desde Stripe:
        - método de pago
        - facturación
        - suscripción
        - cancelación
        """

        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

    # ==========================================================
    # WEBHOOK
    # ==========================================================

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Valida y construye un evento enviado por Stripe.

        La firma debe ser validada antes de procesar
        cualquier webhook.
        """

        if not settings.STRIPE_WEBHOOK_SECRET:
            raise RuntimeError(
                "STRIPE_WEBHOOK_SECRET no está configurada."
            )

        return stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )


stripe_service = StripeService()