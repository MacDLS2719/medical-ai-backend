import asyncio
import os
import sys

import aiohttp
from dotenv import load_dotenv


# ============================================================
# CARGAR VARIABLES DE ENTORNO
# ============================================================

load_dotenv()


PADDLE_ENVIRONMENT = os.getenv(
    "PADDLE_ENVIRONMENT",
    "sandbox"
)

PADDLE_API_KEY = os.getenv("PADDLE_API_KEY")

PADDLE_API_BASE_URL = os.getenv(
    "PADDLE_API_BASE_URL",
    "https://sandbox-api.paddle.com"
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

PADDLE_VERSION = "1"

TIMEOUT = aiohttp.ClientTimeout(total=30)


# ============================================================
# HELPERS
# ============================================================

def print_separator():
    print("=" * 70)


def print_result(
    name: str,
    success: bool,
    status_code: int | None = None,
    detail: str | None = None,
):
    symbol = "OK" if success else "NO"

    print(f"[{symbol}] {name}")

    if status_code is not None:
        print(f"     HTTP: {status_code}")

    if detail:
        print(f"     {detail}")

    print()


async def request_paddle(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
):
    """
    Realiza una petición contra Paddle Sandbox.

    NO modifica información.
    Solamente consulta endpoints.
    """

    url = f"{PADDLE_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"

    headers = {
        "Authorization": f"Bearer {PADDLE_API_KEY}",
        "Content-Type": "application/json",
        "Paddle-Version": PADDLE_VERSION,
    }

    try:
        async with session.request(
            method,
            url,
            headers=headers,
        ) as response:

            text = await response.text()

            try:
                data = await response.json(
                    content_type=None
                )
            except Exception:
                data = {
                    "raw_response": text
                }

            return {
                "success": 200 <= response.status < 300,
                "status_code": response.status,
                "data": data,
                "url": url,
            }

    except aiohttp.ClientError as exc:

        return {
            "success": False,
            "status_code": None,
            "data": {
                "error": str(exc)
            },
            "url": url,
        }


# ============================================================
# TEST PRINCIPAL
# ============================================================

async def main():

    print()
    print_separator()
    print("PADDLE MARKETPLACE / PARTNER API TEST")
    print_separator()
    print()

    print(f"Environment : {PADDLE_ENVIRONMENT}")
    print(f"Base URL    : {PADDLE_API_BASE_URL}")
    print(
        "API Key     : "
        + ("CONFIGURED" if PADDLE_API_KEY else "MISSING")
    )
    print()

    # --------------------------------------------------------
    # Validaciones básicas
    # --------------------------------------------------------

    if not PADDLE_API_KEY:
        print("ERROR: PADDLE_API_KEY no está configurada.")
        sys.exit(1)

    if not PADDLE_API_BASE_URL:
        print("ERROR: PADDLE_API_BASE_URL no está configurada.")
        sys.exit(1)

    # --------------------------------------------------------
    # Crear sesión HTTP
    # --------------------------------------------------------

    async with aiohttp.ClientSession(
        timeout=TIMEOUT
    ) as session:

        # ====================================================
        # PRUEBA 1
        # API GENERAL
        # ====================================================

        print_separator()
        print("1. API GENERAL")
        print_separator()
        print()

        result = await request_paddle(
            session,
            "GET",
            "/event-types",
        )

        if result["success"]:

            print_result(
                "Paddle API",
                True,
                result["status_code"],
                "La API Key funciona correctamente.",
            )

        else:

            print_result(
                "Paddle API",
                False,
                result["status_code"],
                str(result["data"]),
            )

            print_separator()
            print("NO PODEMOS CONTINUAR")
            print_separator()

            return

        # ====================================================
        # PRUEBA 2
        # PARTNER / SELLERS
        # ====================================================

        print_separator()
        print("2. PARTNER API / SELLERS")
        print_separator()
        print()

        # Endpoint de consulta del Partner API.
        # NO crea ningún seller.
        result = await request_paddle(
            session,
            "GET",
            "/sellers",
        )

        if result["success"]:

            print_result(
                "Partner Seller API",
                True,
                result["status_code"],
                "Tu credencial tiene acceso al endpoint de sellers.",
            )

            data = result["data"].get("data", [])

            print(f"     Sellers encontrados: {len(data)}")
            print()

        else:

            print_result(
                "Partner Seller API",
                False,
                result["status_code"],
                str(result["data"]),
            )

            print(
                "     Esto NO significa necesariamente que Paddle "
                "no soporte el modelo."
            )

            print(
                "     Puede significar que tu cuenta todavía "
                "no tiene habilitado Partner API."
            )

            print()

        # ====================================================
        # PRUEBA 3
        # PAYOUTS
        # ====================================================

        print_separator()
        print("3. PAYOUT API")
        print_separator()
        print()

        result = await request_paddle(
            session,
            "GET",
            "/payouts",
        )

        if result["success"]:

            print_result(
                "Payout API",
                True,
                result["status_code"],
                "La API permite consultar payouts.",
            )

            data = result["data"].get("data", [])

            print(f"     Payouts encontrados: {len(data)}")
            print()

            for payout in data[:5]:

                print(
                    f"     - ID: "
                    f"{payout.get('id')}"
                )

                print(
                    f"       Status: "
                    f"{payout.get('status')}"
                )

                print(
                    f"       Amount: "
                    f"{payout.get('amount')}"
                )

                print(
                    f"       Currency: "
                    f"{payout.get('currency_code')}"
                )

                print()

        else:

            print_result(
                "Payout API",
                False,
                result["status_code"],
                str(result["data"]),
            )

        # ====================================================
        # RESULTADO
        # ====================================================

        print_separator()
        print("RESULTADO")
        print_separator()
        print()

        print(
            "La prueba NO crea vendedores, "
            "NO crea pagos y NO mueve dinero."
        )

        print()

        print(
            "Lo que estamos comprobando es si tu cuenta "
            "tiene acceso al modelo Partner/Seller de Paddle."
        )

        print()

        print(
            "Si /sellers devuelve 403/404 por permisos, "
            "necesitamos revisar el acceso Partner de Paddle "
            "antes de continuar."
        )

        print()

        print(
            "Si Seller + Payout funcionan, hacemos la siguiente "
            "prueba: crear un seller Sandbox para representar "
            "a un médico."
        )

        print()

        print_separator()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("Prueba cancelada por el usuario.")
        print()

    except Exception as exc:

        print()
        print_separator()
        print("ERROR NO CONTROLADO")
        print_separator()
        print()
        print(type(exc).__name__)
        print(str(exc))
        print()
        sys.exit(1)

