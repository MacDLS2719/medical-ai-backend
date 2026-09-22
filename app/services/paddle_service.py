import hashlib
import hmac
import time

import httpx

from app.core.config import settings


class PaddleService:
    """
    Servicio centralizado para la comunicación con Paddle.

    La API Key de Paddle se utiliza exclusivamente
    desde el backend.
    """

    def __init__(self) -> None:
        self.api_key = settings.PADDLE_API_KEY
        self.base_url = settings.PADDLE_API_BASE_URL

    # ==========================================================
    # HEADERS
    # ==========================================================

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ==========================================================
    # CLIENT TOKEN (para inicializar Paddle.js en el frontend)
    # ==========================================================

    def get_client_token(self) -> str:
        """
        Retorna el client-side token para inicializar Paddle.js.

        El client token es diferente a la API Key: es un token
        público que va al frontend. Se configura en el .env como
        PADDLE_CLIENT_TOKEN.

        Hasta que se obtenga el token real del Paddle Dashboard
        (Developer Tools → Client-side tokens), se usa como
        placeholder para desarrollo en sandbox.
        """
        token = settings.PADDLE_CLIENT_TOKEN
        if not token:
            # Fallback: usar la API Key en sandbox (solo dev)
            token = self.api_key
        return token

    def get_environment(self) -> str:
        """Retorna el entorno configurado: 'sandbox' o 'production'."""
        return settings.PADDLE_ENVIRONMENT or "sandbox"

    # ==========================================================
    # CREAR CUSTOMER
    # ==========================================================

    async def create_customer(
        self,
        *,
        email: str,
        name: str | None = None,
    ) -> dict:
        """
        Crea un customer en Paddle.
        """

        data: dict = {
            "email": email,
        }

        if name:
            data["name"] = name

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/customers",
                headers=self.headers,
                json=data,
                timeout=30,
            )

        response.raise_for_status()

        return response.json()["data"]

    # ==========================================================
    # OBTENER / BUSCAR CUSTOMER POR EMAIL
    # ==========================================================

    async def get_customer(
        self,
        customer_id: str,
    ) -> dict:
        """
        Obtiene un customer existente.
        """

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/customers/{customer_id}",
                headers=self.headers,
                timeout=30,
            )

        response.raise_for_status()

        return response.json()["data"]

    async def find_customer_by_email(
        self,
        email: str,
    ) -> dict | None:
        """
        Busca un customer en Paddle por su email.
        Retorna el primer resultado exacto o None.
        """

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/customers",
                headers=self.headers,
                params={"search": email},
                timeout=30,
            )

        response.raise_for_status()

        items = response.json().get("data", [])

        for item in items:
            if item.get("email", "").lower() == email.lower():
                return item

        return None

    async def get_or_create_customer(
        self,
        *,
        email: str,
        name: str | None = None,
    ) -> dict:
        """
        Obtiene el customer existente o crea uno nuevo.
        """
        existing = await self.find_customer_by_email(email)
        if existing:
            return existing
        return await self.create_customer(email=email, name=name)

    # ==========================================================
    # OBTENER PRECIO
    # ==========================================================

    async def get_price(
        self,
        price_id: str,
    ) -> dict:
        """
        Obtiene información del Price configurado en Paddle.
        """

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/prices/{price_id}",
                headers=self.headers,
                timeout=30,
            )

        response.raise_for_status()

        return response.json()["data"]

    # ==========================================================
    # OBTENER SUSCRIPCIÓN
    # ==========================================================

    async def get_subscription(
        self,
        subscription_id: str,
    ) -> dict:
        """
        Obtiene una suscripción desde Paddle.
        """

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self.headers,
                timeout=30,
            )

        response.raise_for_status()

        return response.json()["data"]

    # ==========================================================
    # CANCELAR SUSCRIPCIÓN
    # ==========================================================

    async def cancel_subscription(
        self,
        subscription_id: str,
    ) -> dict:
        """
        Cancela una suscripción en Paddle.
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscriptions/{subscription_id}/cancel",
                headers=self.headers,
                json={
                    "effective_at": "next_billing_period",
                },
                timeout=30,
            )

        response.raise_for_status()

        return response.json()["data"]

    # ==========================================================
    # WEBHOOK
    # ==========================================================

    def verify_webhook_signature(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verifica la firma HMAC-SHA256 enviada por Paddle.

        Paddle usa el formato:
            ts=<timestamp>;h1=<hmac-sha256-hex>

        El payload firmado es:
            <timestamp>:<raw_body_bytes>
        """

        webhook_secret = settings.PADDLE_WEBHOOK_SECRET

        if not webhook_secret:
            raise RuntimeError(
                "PADDLE_WEBHOOK_SECRET no está configurado."
            )

        try:
            parts = dict(
                item.split("=", 1)
                for item in signature.split(";")
            )

            timestamp = parts["ts"]
            received_signature = parts["h1"]

        except (ValueError, KeyError):
            return False

        # Rechazar webhooks con más de 5 minutos de antigüedad
        current_time = int(time.time())

        if abs(current_time - int(timestamp)) > 300:
            return False

        # Construir el payload firmado: "<ts>:<body>"
        signed_payload = f"{timestamp}:".encode() + payload

        # HMAC-SHA256
        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            expected_signature,
            received_signature,
        )


paddle_service = PaddleService()