import os
import httpx


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

TOKEN_URL = os.getenv(
    "EMA_TOKEN_URL",
    "https://api.pms.ema.europa.eu/public/v1/oauth2/token"
)

API_BASE_URL = os.getenv(
    "EMA_API_URL",
    "https://api.pms.ema.europa.eu/public/v1"
)

EMA_CLIENT_ID = os.getenv("EMA_CLIENT_ID")
EMA_CLIENT_SECRET = os.getenv("EMA_CLIENT_SECRET")


# ==========================================================
# MAIN
# ==========================================================

async def main():

    print("=" * 70)
    print("MEDICAL AI - PRUEBA EMA PMS PUBLIC API")
    print("=" * 70)

    print()
    print("API:")
    print(API_BASE_URL)

    print()
    print("Verificando credenciales...")

    if not EMA_CLIENT_ID or not EMA_CLIENT_SECRET:
        print()
        print("❌ No se encontraron las credenciales de EMA.")
        print()
        print("Debes configurar:")
        print("  EMA_CLIENT_ID")
        print("  EMA_CLIENT_SECRET")
        print()
        print("La PMS Public API requiere registro y autenticación OAuth2.")
        print("=" * 70)
        return

    # ======================================================
    # 1. OBTENER TOKEN
    # ======================================================

    print()
    print("[1/2] Solicitando token OAuth2 a EMA...")

    token_data = {
        "grant_type": "client_credentials",
        "client_id": EMA_CLIENT_ID,
        "client_secret": EMA_CLIENT_SECRET,
    }

    try:

        async with httpx.AsyncClient(timeout=30.0) as client:

            response = await client.post(
                TOKEN_URL,
                data=token_data,
            )

            print(
                f"HTTP Status token: {response.status_code}"
            )

            print(
                f"URL token: {response.url}"
            )

            if response.status_code != 200:
                print()
                print("❌ No fue posible obtener el token.")
                print()
                print("Respuesta EMA:")
                print(response.text[:2000])
                print("=" * 70)
                return

            token_response = response.json()

            access_token = token_response.get(
                "access_token"
            )

            if not access_token:
                print()
                print("❌ EMA respondió correctamente pero no devolvió access_token.")
                print(response.text[:2000])
                print("=" * 70)
                return

            print()
            print("✓ Token OAuth2 obtenido correctamente.")

            # ==================================================
            # 2. PROBAR API
            # ==================================================

            print()
            print("[2/2] Probando acceso a PMS Public API...")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/fhir+json",
            }

            # Endpoint de Swagger/API pública.
            # Lo dejamos como prueba inicial del acceso.
            response = await client.get(
                API_BASE_URL,
                headers=headers,
            )

            print(
                f"HTTP Status API: {response.status_code}"
            )

            print(
                f"URL final: {response.url}"
            )

            print()
            print("Respuesta inicial:")
            print("-" * 70)

            print(
                response.text[:3000]
            )

            print("-" * 70)

            if response.status_code < 400:
                print()
                print("✓ CONEXIÓN CON EMA PMS EXITOSA")
            else:
                print()
                print("⚠️ El token fue obtenido, pero el endpoint de prueba respondió:")
                print(response.status_code)

    except httpx.HTTPError as e:

        print()
        print("❌ ERROR HTTP:")
        print(e)

    except Exception as e:

        print()
        print("❌ ERROR:")
        print(e)

    print()
    print("=" * 70)
    print("PRUEBA EMA PMS COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())